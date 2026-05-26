#include "RoneatVideoEngine.h"

#define STB_TRUETYPE_IMPLEMENTATION
#include "stb_truetype.h"

#include <cmath>
#include <algorithm>
#include <iostream>
#include <sstream>
#include <fstream>
#include <regex>
#include <cstring>
#include <cstdio>
#include <mutex>
#include <unordered_map>
#include <iomanip>

#ifdef _WIN32
#include <windows.h>
static std::wstring utf8_to_wstring(const std::string& str) {
    if (str.empty()) return L"";
    int size_needed = MultiByteToWideChar(CP_UTF8, 0, &str[0], (int)str.size(), NULL, 0);
    std::wstring wstrTo(size_needed, 0);
    MultiByteToWideChar(CP_UTF8, 0, &str[0], (int)str.size(), &wstrTo[0], size_needed);
    return wstrTo;
}
#endif

#ifdef _MSC_VER
#define popen _popen
#define pclose _pclose
#endif

// ─── Font Caching ────────────────────────────────────────────────────────────
struct CachedFont {
    std::vector<unsigned char> bytes;
    stbtt_fontinfo info;
};

static const CachedFont* get_cached_font(const std::string& font_path) {
    static std::mutex font_mutex;
    static std::unordered_map<std::string, std::shared_ptr<CachedFont>> font_cache;

    std::lock_guard<std::mutex> lock(font_mutex);
    auto it = font_cache.find(font_path);
    if (it != font_cache.end()) {
        return it->second.get();
    }

#ifdef _WIN32
    std::ifstream file(utf8_to_wstring(font_path).c_str(), std::ios::binary | std::ios::ate);
#else
    std::ifstream file(font_path, std::ios::binary | std::ios::ate);
#endif
    if (!file.is_open()) {
        return nullptr;
    }
    std::streamsize size = file.tellg();
    file.seekg(0, std::ios::beg);
    
    auto cf = std::make_shared<CachedFont>();
    cf->bytes.resize(size);
    if (file.read(reinterpret_cast<char*>(cf->bytes.data()), size)) {
        if (stbtt_InitFont(&cf->info, cf->bytes.data(), stbtt_GetFontOffsetForIndex(cf->bytes.data(), 0))) {
            font_cache[font_path] = cf;
            return cf.get();
        }
    }
    return nullptr;
}

// ─── Glyph Caching ───────────────────────────────────────────────────────────
struct CachedGlyph {
    int width = 0;
    int height = 0;
    int xoff = 0;
    int yoff = 0;
    int advance_width = 0;
    int left_side_bearing = 0;
    std::vector<unsigned char> bitmap;
};

struct GlyphKey {
    std::string font_path;
    float font_size;
    uint32_t codepoint;

    bool operator==(const GlyphKey& other) const {
        return font_path == other.font_path &&
               font_size == other.font_size &&
               codepoint == other.codepoint;
    }
};

namespace std {
    template <>
    struct hash<GlyphKey> {
        size_t operator()(const GlyphKey& k) const {
            size_t h1 = std::hash<std::string>{}(k.font_path);
            size_t h2 = std::hash<float>{}(k.font_size);
            size_t h3 = std::hash<uint32_t>{}(k.codepoint);
            return h1 ^ (h2 << 1) ^ (h3 << 2);
        }
    };
}

static const CachedGlyph* get_cached_glyph(const std::string& font_path, float font_size, uint32_t codepoint, const stbtt_fontinfo& font_info) {
    static std::mutex cache_mutex;
    static std::unordered_map<GlyphKey, CachedGlyph> cache;

    std::lock_guard<std::mutex> lock(cache_mutex);
    GlyphKey key{font_path, font_size, codepoint};
    auto it = cache.find(key);
    if (it != cache.end()) {
        return &it->second;
    }

    float scale = stbtt_ScaleForPixelHeight(&font_info, font_size);
    int glyph = stbtt_FindGlyphIndex(&font_info, codepoint);
    if (glyph == 0) return nullptr;

    CachedGlyph cg;
    int gw, gh, gxoff, gyoff;
    unsigned char* bitmap = stbtt_GetGlyphBitmap(&font_info, scale, scale, glyph, &gw, &gh, &gxoff, &gyoff);
    if (bitmap) {
        cg.width = gw;
        cg.height = gh;
        cg.xoff = gxoff;
        cg.yoff = gyoff;
        cg.bitmap.assign(bitmap, bitmap + (gw * gh));
        stbtt_FreeBitmap(bitmap, nullptr);
    }
    stbtt_GetGlyphHMetrics(&font_info, glyph, &cg.advance_width, &cg.left_side_bearing);

    cache[key] = std::move(cg);
    return &cache[key];
}

// ─── UTF-8 to UTF-32 (Unicode Codepoints) Decoder ────────────────────────────
static std::vector<uint32_t> utf8_to_utf32(const std::string& str) {
    std::vector<uint32_t> result;
    for (size_t i = 0; i < str.length(); ) {
        uint32_t cp = 0;
        unsigned char c = str[i];
        size_t len = 0;
        if (c < 0x80) {
            cp = c;
            len = 1;
        } else if ((c & 0xE0) == 0xC0) {
            cp = c & 0x1F;
            len = 2;
        } else if ((c & 0xF0) == 0xE0) {
            cp = c & 0x0F;
            len = 3;
        } else if ((c & 0xF8) == 0xF0) {
            cp = c & 0x07;
            len = 4;
        } else {
            i++;
            continue;
        }
        if (i + len > str.length()) {
            break;
        }
        for (size_t j = 1; j < len; j++) {
            cp = (cp << 6) | (str[i + j] & 0x3F);
        }
        result.push_back(cp);
        i += len;
    }
    return result;
}

// ─── Text Width Measurement using stb_truetype ──────────────────────────────
static int get_text_width(const std::string& text, const std::string& font_path, const stbtt_fontinfo& font, float font_size) {
    std::vector<uint32_t> codepoints = utf8_to_utf32(text);
    float scale = stbtt_ScaleForPixelHeight(&font, font_size);
    float current_x = 0;
    for (size_t i = 0; i < codepoints.size(); i++) {
        uint32_t cp = codepoints[i];
        const CachedGlyph* cg = get_cached_glyph(font_path, font_size, cp, font);
        if (!cg) continue;
        current_x += cg->advance_width * scale;
        if (i < codepoints.size() - 1) {
            int next_glyph = stbtt_FindGlyphIndex(&font, codepoints[i + 1]);
            int kern = stbtt_GetGlyphKernAdvance(&font, stbtt_FindGlyphIndex(&font, cp), next_glyph);
            current_x += kern * scale;
        }
    }
    return static_cast<int>(current_x);
}

// ─── Text Blitter with Alpha Blend ───────────────────────────────────────────
static void draw_text(uint8_t* buffer, int W, int H, const std::string& text, int x_start, int y_start, uint32_t color_rgb, const std::string& font_path, const stbtt_fontinfo& font, float font_size) {
    std::vector<uint32_t> codepoints = utf8_to_utf32(text);
    float scale = stbtt_ScaleForPixelHeight(&font, font_size);
    int ascent, descent, lineGap;
    stbtt_GetFontVMetrics(&font, &ascent, &descent, &lineGap);
    float baseline_y = y_start + ascent * scale;

    uint8_t r = (color_rgb >> 16) & 0xFF;
    uint8_t g = (color_rgb >> 8) & 0xFF;
    uint8_t b = color_rgb & 0xFF;

    float current_x = x_start;
    for (size_t i = 0; i < codepoints.size(); i++) {
        uint32_t cp = codepoints[i];
        const CachedGlyph* cg = get_cached_glyph(font_path, font_size, cp, font);
        if (!cg) continue;

        if (!cg->bitmap.empty()) {
            int draw_x = current_x + cg->xoff;
            int draw_y = baseline_y + cg->yoff;
            int gw = cg->width;
            int gh = cg->height;
            const unsigned char* bitmap = cg->bitmap.data();

            for (int y = 0; y < gh; y++) {
                int py = draw_y + y;
                if (py < 0 || py >= H) continue;
                for (int x = 0; x < gw; x++) {
                    int px = draw_x + x;
                    if (px < 0 || px >= W) continue;
                    
                    uint8_t alpha = bitmap[y * gw + x];
                    if (alpha > 0) {
                        size_t pixel_idx = (py * W + px) * 3;
                        buffer[pixel_idx]     = (buffer[pixel_idx] * (255 - alpha) + r * alpha) / 255;
                        buffer[pixel_idx + 1] = (buffer[pixel_idx + 1] * (255 - alpha) + g * alpha) / 255;
                        buffer[pixel_idx + 2] = (buffer[pixel_idx + 2] * (255 - alpha) + b * alpha) / 255;
                    }
                }
            }
        }

        current_x += cg->advance_width * scale;
        if (i < codepoints.size() - 1) {
            int next_glyph = stbtt_FindGlyphIndex(&font, codepoints[i + 1]);
            int kern = stbtt_GetGlyphKernAdvance(&font, stbtt_FindGlyphIndex(&font, cp), next_glyph);
            current_x += kern * scale;
        }
    }
}

// ─── Rounded Rectangle Drawer with Anti-Aliased Corners ──────────────────────
static void draw_rounded_rect(uint8_t* buffer, int W, int H, int x0, int y0, int x1, int y1, int r, uint32_t color_rgb) {
    if (x0 > x1) std::swap(x0, x1);
    if (y0 > y1) std::swap(y0, y1);
    
    int rx0 = std::max(0, x0);
    int rx1 = std::min(W - 1, x1);
    int ry0 = std::max(0, y0);
    int ry1 = std::min(H - 1, y1);

    uint8_t cr = (color_rgb >> 16) & 0xFF;
    uint8_t cg = (color_rgb >> 8) & 0xFF;
    uint8_t cb = color_rgb & 0xFF;

    int width = x1 - x0;
    int height = y1 - y0;
    
    r = std::max(0, std::min({r, width / 2, height / 2}));

    for (int y = ry0; y <= ry1; y++) {
        for (int x = rx0; x <= rx1; x++) {
            double alpha = 1.0;
            // Top-left corner
            if (x < x0 + r && y < y0 + r) {
                double dx = x - (x0 + r);
                double dy = y - (y0 + r);
                double dist = std::sqrt(dx*dx + dy*dy);
                if (dist > r + 0.5) alpha = 0.0;
                else if (dist > r - 0.5) alpha = (r + 0.5 - dist);
            }
            // Top-right corner
            else if (x > x1 - r && y < y0 + r) {
                double dx = x - (x1 - r);
                double dy = y - (y0 + r);
                double dist = std::sqrt(dx*dx + dy*dy);
                if (dist > r + 0.5) alpha = 0.0;
                else if (dist > r - 0.5) alpha = (r + 0.5 - dist);
            }
            // Bottom-left corner
            else if (x < x0 + r && y > y1 - r) {
                double dx = x - (x0 + r);
                double dy = y - (y1 - r);
                double dist = std::sqrt(dx*dx + dy*dy);
                if (dist > r + 0.5) alpha = 0.0;
                else if (dist > r - 0.5) alpha = (r + 0.5 - dist);
            }
            // Bottom-right corner
            else if (x > x1 - r && y > y1 - r) {
                double dx = x - (x1 - r);
                double dy = y - (y1 - r);
                double dist = std::sqrt(dx*dx + dy*dy);
                if (dist > r + 0.5) alpha = 0.0;
                else if (dist > r - 0.5) alpha = (r + 0.5 - dist);
            }

            if (alpha > 0.0) {
                size_t pixel_idx = (y * W + x) * 3;
                if (alpha >= 1.0) {
                    buffer[pixel_idx]     = cr;
                    buffer[pixel_idx + 1] = cg;
                    buffer[pixel_idx + 2] = cb;
                } else {
                    buffer[pixel_idx]     = static_cast<uint8_t>(buffer[pixel_idx] * (1.0 - alpha) + cr * alpha);
                    buffer[pixel_idx + 1] = static_cast<uint8_t>(buffer[pixel_idx + 1] * (1.0 - alpha) + cg * alpha);
                    buffer[pixel_idx + 2] = static_cast<uint8_t>(buffer[pixel_idx + 2] * (1.0 - alpha) + cb * alpha);
                }
            }
        }
    }
}

// ─── Color Helpers ───────────────────────────────────────────────────────────
static uint32_t hex_to_rgb(const std::string& hex_str) {
    std::string s = hex_str;
    if (!s.empty() && s[0] == '#') {
        s = s.substr(1);
    }
    if (s.length() != 6) {
        return 0xC8A96E;
    }
    uint32_t val = 0;
    std::stringstream ss;
    ss << std::hex << s;
    ss >> val;
    return val;
}

static uint32_t lerp_color(uint32_t c1, uint32_t c2, double t) {
    uint8_t r1 = (c1 >> 16) & 0xFF, g1 = (c1 >> 8) & 0xFF, b1 = c1 & 0xFF;
    uint8_t r2 = (c2 >> 16) & 0xFF, g2 = (c2 >> 8) & 0xFF, b2 = c2 & 0xFF;
    uint8_t r = static_cast<uint8_t>(r1 + (r2 - r1) * t);
    uint8_t g = static_cast<uint8_t>(g1 + (g2 - g1) * t);
    uint8_t b = static_cast<uint8_t>(b1 + (b2 - b1) * t);
    return (r << 16) | (g << 8) | b;
}

static uint32_t shade_color(uint32_t color, int amount) {
    int r = static_cast<int>((color >> 16) & 0xFF) + amount;
    int g = static_cast<int>((color >> 8) & 0xFF) + amount;
    int b = static_cast<int>(color & 0xFF) + amount;
    r = std::max(0, std::min(255, r));
    g = std::max(0, std::min(255, g));
    b = std::max(0, std::min(255, b));
    return (r << 16) | (g << 8) | b;
}

// ─── Note Translation Mapper ─────────────────────────────────────────────────
static std::string translate_note(int index, const std::string& mode) {
    if (index < 1 || index > 21) {
        return "";
    }
    if (mode == "Numeric") {
        return std::to_string(index);
    }
    int octave = ((index - 1) / 7) + 1;
    const std::string letters[] = {
        "G", "A", "B", "C", "D", "E", "F",
        "G", "A", "B", "C", "D", "E", "F",
        "G", "A", "B", "C", "D", "E", "F"
    };
    const std::string syllabic[] = {
        "Sol", "La", "Si", "Do", "Re", "Mi", "Fa",
        "Sol", "La", "Si", "Do", "Re", "Mi", "Fa",
        "Sol", "La", "Si", "Do", "Re", "Mi", "Fa"
    };
    if (mode == "Letters") {
        return letters[index - 1] + std::to_string(octave);
    }
    if (mode == "Syllabic") {
        return syllabic[index - 1] + std::to_string(octave);
    }
    return std::to_string(index);
}

// ─── WAV File Format Structs ──────────────────────────────────────────────────
struct WAVHeader {
    char riff[4] = {'R', 'I', 'F', 'F'};
    uint32_t overall_size;
    char wave[4] = {'W', 'A', 'V', 'E'};
    char fmt_chunk_marker[4] = {'f', 'm', 't', ' '};
    uint32_t length_of_fmt = 16;
    uint16_t format_type = 3; // 3 = IEEE Float
    uint16_t channels = 1;
    uint32_t sample_rate;
    uint32_t byterate;
    uint16_t block_align;
    uint16_t bits_per_sample = 32;
    char data_chunk_header[4] = {'d', 'a', 't', 'a'};
    uint32_t data_size;
};

static bool write_wav_file(const std::string& filename, const float* data, size_t num_samples, uint32_t sample_rate) {
#ifdef _WIN32
    std::ofstream file(utf8_to_wstring(filename).c_str(), std::ios::binary);
#else
    std::ofstream file(filename, std::ios::binary);
#endif
    if (!file.is_open()) return false;

    WAVHeader header;
    header.sample_rate = sample_rate;
    header.channels = 1;
    header.bits_per_sample = 32;
    header.format_type = 3; // IEEE float
    header.block_align = (header.channels * header.bits_per_sample) / 8;
    header.byterate = header.sample_rate * header.block_align;
    header.data_size = num_samples * sizeof(float);
    header.overall_size = header.data_size + 36;

    file.write(reinterpret_cast<const char*>(&header), sizeof(header));
    file.write(reinterpret_cast<const char*>(data), header.data_size);
    return true;
}

// ─── RoneatVideoEngine Class Methods ──────────────────────────────────────────

RoneatVideoEngine::RoneatVideoEngine() {}
RoneatVideoEngine::~RoneatVideoEngine() {}

std::vector<VideoEvent> RoneatVideoEngine::build_timeline(
    const std::string& score_text,
    int bpm,
    double hits_per_sec,
    py::object sync_data_py,
    double tail_sec
) {
    const int N_BARS = 21;
    bpm = std::max(20, std::min(bpm, 400));
    double beat_sec = 60.0 / bpm;
    double dt_hit = 1.0 / std::max(1.0, hits_per_sec);

    std::vector<VideoEvent> events;
    double cursor = 0.0;

    if (!sync_data_py.is_none()) {
        py::list sync_data = py::cast<py::list>(sync_data_py);
        if (sync_data.size() > 0) {
            double t0 = 0.0;
            py::dict first_item = py::cast<py::dict>(sync_data[0]);
            if (first_item.contains("time")) {
                t0 = first_item["time"].cast<double>();
            }
            
            for (size_t i = 0; i < sync_data.size(); i++) {
                py::dict item = py::cast<py::dict>(sync_data[i]);
                double t_abs = 0.0;
                if (item.contains("time")) {
                    t_abs = item["time"].cast<double>() - t0;
                }
                
                double t_next_abs = t_abs + beat_sec;
                if (i + 1 < sync_data.size()) {
                    py::dict next_item = py::cast<py::dict>(sync_data[i + 1]);
                    if (next_item.contains("time")) {
                        t_next_abs = next_item["time"].cast<double>() - t0;
                    }
                }
                double slot_dur = std::max(0.05, t_next_abs - t_abs);

                std::string tok = "-";
                if (item.contains("note")) {
                    tok = item["note"].cast<std::string>();
                }

                if (tok == "/" || tok == "_") {
                    continue;
                }

                if (tok == "-" || tok == "0" || tok == "x" || tok == "") {
                    events.push_back(VideoEvent(t_abs, slot_dur, std::nullopt, std::nullopt, false, 0, 1));
                    continue;
                }

                std::regex lr_re(R"(^\((\d+)\)(\d+)(#(\d+))?$)");
                std::regex tok_re(R"(^(\d+)(#(\d+))?$)");

                std::smatch m_lr;
                if (std::regex_match(tok, m_lr, lr_re)) {
                    int left_bar = std::stoi(m_lr[1].str());
                    int bar = std::stoi(m_lr[2].str());
                    if (bar < 1 || bar > 21 || left_bar < 1 || left_bar > 21) {
                        events.push_back(VideoEvent(t_abs, slot_dur, std::nullopt, std::nullopt, false, 0, 1));
                        continue;
                    }

                    if (m_lr[3].matched) {
                        int repeat = 1;
                        if (m_lr[4].matched) {
                            repeat = std::max(1, std::min(std::stoi(m_lr[4].str()), 32));
                        }
                        double sub_dt = slot_dur / repeat;
                        for (int h = 0; h < repeat; h++) {
                            events.push_back(VideoEvent(
                                t_abs + h * sub_dt,
                                sub_dt,
                                bar,
                                left_bar,
                                true,
                                h,
                                repeat
                            ));
                        }
                    } else {
                        events.push_back(VideoEvent(t_abs, slot_dur, bar, left_bar, false, 0, 1));
                    }
                    continue;
                }

                std::smatch m;
                if (std::regex_match(tok, m, tok_re)) {
                    int bar = std::stoi(m[1].str());
                    if (bar < 1 || bar > 21) {
                        events.push_back(VideoEvent(t_abs, slot_dur, std::nullopt, std::nullopt, false, 0, 1));
                        continue;
                    }

                    if (m[2].matched) {
                        int repeat = 1;
                        if (m[3].matched) {
                            repeat = std::max(1, std::min(std::stoi(m[3].str()), 32));
                        }
                        double sub_dt = slot_dur / repeat;
                        for (int h = 0; h < repeat; h++) {
                            events.push_back(VideoEvent(
                                t_abs + h * sub_dt,
                                sub_dt,
                                bar,
                                bar + 7,
                                true,
                                h,
                                repeat
                            ));
                        }
                    } else {
                        events.push_back(VideoEvent(t_abs, slot_dur, bar, bar + 7, false, 0, 1));
                    }
                    continue;
                }

                events.push_back(VideoEvent(t_abs, slot_dur, std::nullopt, std::nullopt, false, 0, 1));
            }
        }
    } else {
        std::vector<std::string> tokens;
        std::stringstream ss(score_text);
        std::string item;
        while (ss >> item) {
            tokens.push_back(item);
        }

        std::regex lr_re(R"(^\((\d+)\)(\d+)(#(\d+))?$)");
        std::regex tok_re(R"(^(\d+)(#(\d+))?$)");

        for (const auto& raw : tokens) {
            if (raw == "/" || raw == "_") {
                continue;
            }

            if (raw == "-" || raw == "0" || raw == "x" || raw == "") {
                events.push_back(VideoEvent(cursor, beat_sec, std::nullopt, std::nullopt, false, 0, 1));
                cursor += beat_sec;
                continue;
            }

            std::smatch m_lr;
            if (std::regex_match(raw, m_lr, lr_re)) {
                int left_bar = std::stoi(m_lr[1].str());
                int bar = std::stoi(m_lr[2].str());
                if (bar < 1 || bar > 21 || left_bar < 1 || left_bar > 21) {
                    events.push_back(VideoEvent(cursor, beat_sec, std::nullopt, std::nullopt, false, 0, 1));
                    cursor += beat_sec;
                    continue;
                }

                if (m_lr[3].matched) {
                    int repeat = 1;
                    if (m_lr[4].matched) {
                        repeat = std::max(1, std::min(std::stoi(m_lr[4].str()), 32));
                    }
                    double total_dur = repeat * dt_hit;
                    for (int h = 0; h < repeat; h++) {
                        events.push_back(VideoEvent(
                            cursor + h * dt_hit,
                            dt_hit,
                            bar,
                            left_bar,
                            true,
                            h,
                            repeat
                        ));
                    }
                    cursor += total_dur;
                } else {
                    events.push_back(VideoEvent(cursor, beat_sec, bar, left_bar, false, 0, 1));
                    cursor += beat_sec;
                }
                continue;
            }

            std::smatch m;
            if (!std::regex_match(raw, m, tok_re)) {
                events.push_back(VideoEvent(cursor, beat_sec, std::nullopt, std::nullopt, false, 0, 1));
                cursor += beat_sec;
                continue;
            }

            int bar = std::stoi(m[1].str());
            if (bar < 1 || bar > 21) {
                events.push_back(VideoEvent(cursor, beat_sec, std::nullopt, std::nullopt, false, 0, 1));
                cursor += beat_sec;
                continue;
            }

            if (m[2].matched) {
                int repeat = 1;
                if (m[3].matched) {
                    repeat = std::max(1, std::min(std::stoi(m[3].str()), 32));
                }
                double total_dur = repeat * dt_hit;
                for (int h = 0; h < repeat; h++) {
                    events.push_back(VideoEvent(
                        cursor + h * dt_hit,
                        dt_hit,
                        bar,
                        bar + 7,
                        true,
                        h,
                        repeat
                    ));
                }
                cursor += total_dur;
            } else {
                events.push_back(VideoEvent(cursor, beat_sec, bar, bar + 7, false, 0, 1));
                cursor += beat_sec;
            }
        }
    }

    double tail_start = 0.0;
    if (!events.empty()) {
        tail_start = events.back().t_start + events.back().duration;
    }
    if (tail_sec > 0.0) {
        events.push_back(VideoEvent(tail_start, tail_sec, std::nullopt, std::nullopt, false, 0, 1));
    }

    return events;
}

py::array_t<uint8_t> RoneatVideoEngine::render_frame(
    std::optional<int> active_bar,
    std::optional<int> active_left_bar,
    double frame_t,
    double event_t,
    double event_dur,
    int W,
    int H,
    bool dark_mode,
    const std::string& song_title,
    bool two_mallets,
    const std::string& accent_hex,
    const std::string& view_mode,
    bool is_tremolo_hit,
    int sub_hit,
    int total_hits,
    double title_scale,
    double label_scale,
    double status_scale,
    double title_y_offset,
    double label_y_offset,
    double status_y_offset,
    bool show_labels,
    bool show_status,
    const std::string& font_path,
    py::object title_img
) {
    const int N_BARS = 21;

    // ── Colour palette ─────────────────────────────────────────────────────
    uint32_t BG, RAIL, BAR_FACE, BAR_SHADE, TUBE, LABEL, LH_FACE, LH_SHADE, STATUS, TITLE_C, GRID_LINE;
    if (dark_mode) {
        BG          = 0x0A0C12;
        RAIL        = 0x1E2434;
        BAR_FACE    = 0x202A42;
        BAR_SHADE   = 0x141C30;
        TUBE        = 0x182034;
        LABEL       = 0x50648C;
        LH_FACE     = 0x1C488C;
        LH_SHADE    = 0x12346E;
        STATUS      = 0xAA8C4B;
        TITLE_C     = 0xD2B278;
        GRID_LINE   = 0x161C2C;
    } else {
        BG          = 0xF2ECE1;
        RAIL        = 0x877352;
        BAR_FACE    = 0xC0AC82;
        BAR_SHADE   = 0x9B875F;
        TUBE        = 0xD2C4A2;
        LABEL       = 0x5A4626;
        LH_FACE     = 0x305FAF;
        LH_SHADE    = 0x417DC3;
        STATUS      = 0x6C4E16;
        TITLE_C     = 0x583A0C;
        GRID_LINE   = 0xDCD2B9;
    }

    uint32_t ACCENT = hex_to_rgb(accent_hex);

    // ── Progress & Attack Envelope ─────────────────────────────────────────
    double progress = (frame_t - event_t) / std::max(event_dur, 1e-6);
    progress = std::max(0.0, std::min(1.0, progress));
    double hit_flash = std::exp(-progress * 8.0);

    // ── Canvas Setup ───────────────────────────────────────────────────────
    std::vector<uint8_t> frame_buffer(W * H * 3);
    uint8_t bg_r = (BG >> 16) & 0xFF;
    uint8_t bg_g = (BG >> 8) & 0xFF;
    uint8_t bg_b = BG & 0xFF;
    for (int i = 0; i < W * H; i++) {
        frame_buffer[i * 3]     = bg_r;
        frame_buffer[i * 3 + 1] = bg_g;
        frame_buffer[i * 3 + 2] = bg_b;
    }

    // ── Load Font ──────────────────────────────────────────────────────────
    const CachedFont* cf = get_cached_font(font_path);
    bool font_loaded = (cf != nullptr);

    // ── Song Title ─────────────────────────────────────────────────────────
    int title_h = 0;
    if (!song_title.empty() || !title_img.is_none()) {
        title_h = static_cast<int>(H * 0.1);
        if (title_img.is_none()) {
            if (font_loaded) {
                float min_wh = std::min(W, H);
                float tf_size = std::max(24.0f, min_wh * 0.077f) * title_scale;
                int tw = get_text_width(song_title, font_path, cf->info, tf_size);
                int tx = (W - tw) / 2;
                int ty = static_cast<int>(H * 0.033) + static_cast<int>(H * title_y_offset);
                draw_text(frame_buffer.data(), W, H, song_title, tx, ty, TITLE_C, font_path, cf->info, tf_size);
            }
        } else {
            py::array_t<uint8_t> title_arr = py::cast<py::array_t<uint8_t>>(title_img);
            auto title_buf = title_arr.request();
            if (title_buf.ndim == 3 && title_buf.shape[2] == 4) {
                int title_H = title_buf.shape[0];
                int title_W = title_buf.shape[1];
                uint8_t* title_ptr = static_cast<uint8_t*>(title_buf.ptr);
                int x_start = (W - title_W) / 2;
                int y_start = static_cast<int>(H * 0.033) + static_cast<int>(H * title_y_offset);

                for (int ty = 0; ty < title_H; ty++) {
                    int py = y_start + ty;
                    if (py < 0 || py >= H) continue;
                    for (int tx = 0; tx < title_W; tx++) {
                        int px = x_start + tx;
                        if (px < 0 || px >= W) continue;

                        size_t src_idx = (ty * title_W + tx) * 4;
                        uint8_t r_src = title_ptr[src_idx];
                        uint8_t g_src = title_ptr[src_idx + 1];
                        uint8_t b_src = title_ptr[src_idx + 2];
                        uint8_t a_src = title_ptr[src_idx + 3];

                        if (a_src > 0) {
                            size_t dest_idx = (py * W + px) * 3;
                            frame_buffer[dest_idx]     = (frame_buffer[dest_idx] * (255 - a_src) + r_src * a_src) / 255;
                            frame_buffer[dest_idx + 1] = (frame_buffer[dest_idx + 1] * (255 - a_src) + g_src * a_src) / 255;
                            frame_buffer[dest_idx + 2] = (frame_buffer[dest_idx + 2] * (255 - a_src) + b_src * a_src) / 255;
                        }
                    }
                }
            }
        }
    }

    // ── Layout Constants ───────────────────────────────────────────────────
    int pad_x    = std::max(10, static_cast<int>(W * 0.057));
    int gap      = std::max(2, static_cast<int>(W * 0.0036));
    double bar_w = (W - pad_x * 2 - gap * (N_BARS - 1)) / static_cast<double>(N_BARS);
    int rail_top = title_h + static_cast<int>(H * 0.11);
    int rail_h   = std::max(8, static_cast<int>(H * 0.016));
    int avail    = H - rail_top - rail_h - static_cast<int>(H * 0.14);
    int max_bh_avail = static_cast<int>(avail * 0.80);
    int ideal_max_bh = static_cast<int>(W * 0.35);
    int max_bh   = std::min(max_bh_avail, ideal_max_bh);
    int min_bh   = static_cast<int>(max_bh * 0.25);
    
    int extra_h = avail - max_bh;
    if (extra_h > 0) {
        rail_top += static_cast<int>(extra_h * 0.4);
    }

    // Rail (horizontal beam)
    draw_rounded_rect(frame_buffer.data(), W, H, pad_x - 20, rail_top, W - pad_x + 20, rail_top + rail_h, rail_h / 2, RAIL);

    // ── Bars ───────────────────────────────────────────────────────────────
    for (int i = 0; i < N_BARS; i++) {
        int bar_num = N_BARS - i;       // 21 -> 1 left to right
        double t_pos = static_cast<double>(i) / (N_BARS - 1);
        int bh = static_cast<int>(max_bh - t_pos * (max_bh - min_bh));
        int x0 = static_cast<int>(pad_x + i * (bar_w + gap));
        int x1 = static_cast<int>(x0 + bar_w);
        int y0 = rail_top + rail_h;
        int y1 = y0 + bh;
        int cx = (x0 + x1) / 2;
        int bw_int = std::max(1, x1 - x0);
        int max_r = std::min(bw_int / 2, bh / 2);
        int r_slab = std::max(1, std::min(max_r, static_cast<int>(bar_w * 0.14)));

        bool is_rh = (active_bar.has_value() && bar_num == *active_bar);
        
        std::optional<int> lh_target = std::nullopt;
        if (active_left_bar.has_value()) {
            lh_target = *active_left_bar;
        } else if (active_bar.has_value()) {
            lh_target = *active_bar + 7;
        }

        bool is_lh = (two_mallets && lh_target.has_value() && bar_num == *lh_target && bar_num <= N_BARS);

        // Slab body colors
        uint32_t face = BAR_FACE;
        uint32_t shade = BAR_SHADE;
        
        if (is_rh) {
            face = ACCENT;
            shade = shade_color(ACCENT, -40);
        } else if (is_lh) {
            face = LH_FACE;
            shade = LH_SHADE;
        }

        int stripe_w = std::max(0, std::min(bw_int - 1, static_cast<int>(bar_w * 0.15)));
        if (stripe_w == 0 && bw_int > 2) {
            stripe_w = 1;
        }

        // Base shadow (covers the left)
        draw_rounded_rect(frame_buffer.data(), W, H, x0, y0, x1, y1, r_slab, shade);
        // Face (shifted right)
        draw_rounded_rect(frame_buffer.data(), W, H, x0 + stripe_w, y0, x1, y1, r_slab, face);

        // Top highlight (metallic shimmer)
        int shimmer_h = is_rh ? std::max(4, static_cast<int>(bh * 0.15)) : std::max(4, static_cast<int>(bh * 0.08));
        double shimmer_t = is_rh ? (0.35 + 0.65 * hit_flash) : 0.12;
        uint32_t shimmer_c = lerp_color(face, 0xFFFFFF, shimmer_t);
        int margin = std::max(1, static_cast<int>(bar_w * 0.1));

        int sx0 = x0 + stripe_w + margin;
        int sy0 = y0 + margin;
        int sx1 = x1 - margin;
        int sy1 = y0 + shimmer_h + margin;

        int sw = sx1 - sx0;
        int sh = sy1 - sy0;
        int s_r = std::max(1, std::min({sw / 2, sh / 2, r_slab - margin}));

        if (sx1 > sx0 && sy1 > sy0) {
            draw_rounded_rect(frame_buffer.data(), W, H, sx0, sy0, sx1, sy1, s_r, shimmer_c);
        }

        // Note label
        if (show_labels && font_loaded) {
            int lbl_y = y1 + std::max(8, static_cast<int>(H * 0.018)) + static_cast<int>(H * label_y_offset);
            float lbl_sz = std::max(11.0f, std::min(static_cast<float>(bar_w * 0.44f), 22.0f));
            if (view_mode == "Syllabic" || view_mode == "Letters") {
                lbl_sz *= 0.78f;
            }
            lbl_sz *= label_scale;

            uint32_t lc = LABEL;
            if (is_rh) lc = ACCENT;
            else if (is_lh) lc = LH_FACE;

            std::string lbl_text = translate_note(bar_num, view_mode);
            int lbl_w = get_text_width(lbl_text, font_path, cf->info, lbl_sz);
            int lx = cx - lbl_w / 2;
            draw_text(frame_buffer.data(), W, H, lbl_text, lx, lbl_y, lc, font_path, cf->info, lbl_sz);
        }
    }

    // ── Bottom Status Text ─────────────────────────────────────────────────
    if (show_status && active_bar.has_value() && *active_bar >= 1 && *active_bar <= N_BARS && font_loaded) {
        std::string rh_lbl = translate_note(*active_bar, view_mode);
        std::optional<int> lh_n_opt = std::nullopt;
        if (active_left_bar.has_value()) {
            lh_n_opt = *active_left_bar;
        } else {
            lh_n_opt = *active_bar + 7;
        }
        
        std::string status = "";
        if (two_mallets && lh_n_opt.has_value() && *lh_n_opt <= N_BARS) {
            std::string lh_lbl = translate_note(*lh_n_opt, view_mode);
            status = "Right hand: " + rh_lbl + "     Left hand: " + lh_lbl;
        } else {
            status = "Bar: " + rh_lbl;
        }
        if (is_tremolo_hit) {
            status += "     (tremolo " + std::to_string(sub_hit + 1) + "/" + std::to_string(total_hits) + ")";
        }

        float sf_size = std::max(12.0f, static_cast<float>(std::min(W, H) * 0.048f)) * status_scale;
        int sw = get_text_width(status, font_path, cf->info, sf_size);
        int sx = (W - sw) / 2;
        int sy = static_cast<int>(H - H * 0.074) + static_cast<int>(H * status_y_offset);
        draw_text(frame_buffer.data(), W, H, status, sx, sy, STATUS, font_path, cf->info, sf_size);
    }

    // Create py::array_t from raw buffer (copy into Numpy array memory)
    py::array_t<uint8_t> result({H, W, 3});
    auto buf = result.request();
    uint8_t* ptr = static_cast<uint8_t*>(buf.ptr);
    std::memcpy(ptr, frame_buffer.data(), W * H * 3);
    return result;
}

void RoneatVideoEngine::export_mp4(
    const std::string& filepath,
    const std::string& score_text,
    int bpm,
    double hits_per_sec,
    py::array_t<float> audio_arr,
    int audio_rate,
    bool dark_mode,
    const std::string& song_title,
    bool two_mallets,
    const std::string& accent_hex,
    const std::string& view_mode,
    py::object sync_data,
    const std::string& ffmpeg_bin,
    py::object progress_cb,
    int W,
    int H,
    int FPS,
    double title_scale,
    double label_scale,
    double status_scale,
    double title_y_offset,
    double label_y_offset,
    double status_y_offset,
    bool show_labels,
    bool show_status,
    const std::string& font_path,
    py::object title_img
) {
    // ── 1. Build timeline ──────────────────────────────────────────────────
    std::vector<VideoEvent> events = build_timeline(score_text, bpm, hits_per_sec, sync_data);
    if (events.empty()) {
        throw std::runtime_error("Empty timeline. Nothing to export.");
    }
    
    double last_t = events.back().t_start + events.back().duration;
    int total_frames = std::max(1, static_cast<int>(last_t * FPS));

    // Pre-calculate start and end frames for lookup speed
    struct FramedEvent {
        int f0;
        int f1;
        VideoEvent ev;
    };
    std::vector<FramedEvent> framed_events;
    for (const auto& ev : events) {
        int f0 = static_cast<int>(ev.t_start * FPS);
        int f1 = std::max(f0 + 1, static_cast<int>((ev.t_start + ev.duration) * FPS));
        framed_events.push_back({f0, f1, ev});
    }

    size_t current_ev_idx = 0;
    auto get_event_at_frame = [&](int fi) -> VideoEvent {
        while (current_ev_idx < framed_events.size()) {
            const auto& fe = framed_events[current_ev_idx];
            if (fi >= fe.f0 && fi < fe.f1) {
                return fe.ev;
            }
            if (fi >= fe.f1) {
                current_ev_idx++;
            } else {
                break;
            }
        }
        for (size_t i = 0; i < framed_events.size(); i++) {
            const auto& fe = framed_events[i];
            if (fi >= fe.f0 && fi < fe.f1) {
                current_ev_idx = i;
                return fe.ev;
            }
        }
        VideoEvent last_ev = events.back();
        last_ev.bar = std::nullopt;
        last_ev.left_bar = std::nullopt;
        return last_ev;
    };

    // ── 2. Write Temporary WAV file ────────────────────────────────────────
    std::string tmp_wav = filepath + "_tmp_audio.wav";
    auto audio_buf = audio_arr.request();
    float* audio_data = static_cast<float*>(audio_buf.ptr);
    size_t audio_samples = audio_buf.size;
    if (!write_wav_file(tmp_wav, audio_data, audio_samples, audio_rate)) {
        throw std::runtime_error("Failed to write temporary audio WAV file: " + tmp_wav);
    }

    // ── 3. Start ffmpeg process pipe ───────────────────────────────────────
    // Build ffmpeg command line
    std::string cmd = "\"" + ffmpeg_bin + "\" -y -f rawvideo -pix_fmt rgb24 -s " 
                      + std::to_string(W) + "x" + std::to_string(H) + " -r " + std::to_string(FPS) 
                      + " -i - -i \"" + tmp_wav + "\" -c:v libx264 -crf 18 -preset fast -pix_fmt yuv420p -c:a aac -b:a 192k -shortest \"" + filepath + "\"";

#ifdef _WIN32
    std::string run_cmd = "\"" + cmd + "\"";
#else
    std::string run_cmd = cmd;
#endif

#ifdef _WIN32
    FILE* ffmpeg_pipe = _wpopen(utf8_to_wstring(run_cmd).c_str(), L"wb");
#else
    FILE* ffmpeg_pipe = popen(run_cmd.c_str(), "wb");
#endif

    if (!ffmpeg_pipe) {
#ifdef _WIN32
        _wremove(utf8_to_wstring(tmp_wav).c_str());
#else
        std::remove(tmp_wav.c_str());
#endif
        throw std::runtime_error("Failed to launch ffmpeg process pipe: " + cmd);
    }

    // ── 4. Render and stream frames ────────────────────────────────────────
    for (int fi = 0; fi < total_frames; fi++) {
        VideoEvent ev = get_event_at_frame(fi);
        double frame_t = static_cast<double>(fi) / FPS;

        py::array_t<uint8_t> frame_arr = render_frame(
            ev.bar,
            ev.left_bar,
            frame_t,
            ev.t_start,
            ev.duration,
            W, H,
            dark_mode,
            song_title,
            two_mallets,
            accent_hex,
            view_mode,
            ev.is_tremolo_hit,
            ev.sub_hit,
            ev.total_hits,
            title_scale,
            label_scale,
            status_scale,
            title_y_offset,
            label_y_offset,
            status_y_offset,
            show_labels,
            show_status,
            font_path,
            title_img
        );

        auto f_buf = frame_arr.request();
        uint8_t* f_ptr = static_cast<uint8_t*>(f_buf.ptr);
        size_t written = std::fwrite(f_ptr, 1, W * H * 3, ffmpeg_pipe);
        if (written < static_cast<size_t>(W * H * 3)) {
            pclose(ffmpeg_pipe);
#ifdef _WIN32
            _wremove(utf8_to_wstring(tmp_wav).c_str());
#else
            std::remove(tmp_wav.c_str());
#endif
            throw std::runtime_error("Failed to write frame to ffmpeg pipe.");
        }

        if (!progress_cb.is_none() && (fi % 30 == 0 || fi == total_frames - 1)) {
            double fraction = static_cast<double>(fi) / total_frames;
            std::string label = "Frame " + std::to_string(fi + 1) + "/" + std::to_string(total_frames);
            progress_cb(fraction, label);
        }
    }

    // Close the pipe and wait for ffmpeg to finish
    int res = pclose(ffmpeg_pipe);
#ifdef _WIN32
    _wremove(utf8_to_wstring(tmp_wav).c_str());
#else
    std::remove(tmp_wav.c_str());
#endif

    if (res != 0) {
        throw std::runtime_error("ffmpeg process failed with exit code " + std::to_string(res));
    }

    if (!progress_cb.is_none()) {
        progress_cb(1.0, "Done!");
    }
}
