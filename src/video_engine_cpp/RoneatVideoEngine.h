#pragma once

#ifndef NOMINMAX
#define NOMINMAX
#endif

#include <vector>
#include <string>
#include <optional>
#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>

namespace py = pybind11;

struct VideoEvent {
    double t_start;
    double duration;
    std::optional<int> bar;
    std::optional<int> left_bar;
    bool is_tremolo_hit = false;
    int sub_hit = 0;
    int total_hits = 1;

    VideoEvent(double t_start_, double duration_, std::optional<int> bar_, 
               std::optional<int> left_bar_ = std::nullopt, bool is_tremolo_hit_ = false, 
               int sub_hit_ = 0, int total_hits_ = 1)
        : t_start(t_start_), duration(duration_), bar(bar_), left_bar(left_bar_), 
          is_tremolo_hit(is_tremolo_hit_), sub_hit(sub_hit_), total_hits(total_hits_) {}
};

class RoneatVideoEngine {
public:
    RoneatVideoEngine();
    ~RoneatVideoEngine();

    std::vector<VideoEvent> build_timeline(
        const std::string& score_text,
        int bpm,
        double hits_per_sec,
        py::object sync_data = py::none(),
        double tail_sec = 2.0
    );

    py::array_t<uint8_t> render_frame(
        std::optional<int> active_bar,
        std::optional<int> active_left_bar,
        double frame_t,
        double event_t,
        double event_dur,
        int W = 1920,
        int H = 1080,
        bool dark_mode = true,
        const std::string& song_title = "",
        bool two_mallets = true,
        const std::string& accent_hex = "#c8a96e",
        const std::string& view_mode = "Numeric",
        bool is_tremolo_hit = false,
        int sub_hit = 0,
        int total_hits = 1,
        double title_scale = 1.0,
        double label_scale = 1.0,
        double status_scale = 1.0,
        double title_y_offset = 0.0,
        double label_y_offset = 0.0,
        double status_y_offset = 0.0,
        bool show_labels = true,
        bool show_status = true,
        const std::string& font_path = "Arial.ttf",
        py::object title_img = py::none()
    );

    void export_mp4(
        const std::string& filepath,
        const std::string& score_text,
        int bpm,
        double hits_per_sec,
        py::array_t<float> audio_arr,
        int audio_rate,
        bool dark_mode = true,
        const std::string& song_title = "",
        bool two_mallets = true,
        const std::string& accent_hex = "#c8a96e",
        const std::string& view_mode = "Numeric",
        py::object sync_data = py::none(),
        const std::string& ffmpeg_bin = "ffmpeg",
        py::object progress_cb = py::none(),
        int W = 1920,
        int H = 1080,
        int FPS = 60,
        double title_scale = 1.0,
        double label_scale = 1.0,
        double status_scale = 1.0,
        double title_y_offset = 0.0,
        double label_y_offset = 0.0,
        double status_y_offset = 0.0,
        bool show_labels = true,
        bool show_status = true,
        const std::string& font_path = "Arial.ttf",
        py::object title_img = py::none()
    );
};
