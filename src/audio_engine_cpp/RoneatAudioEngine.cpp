#include "RoneatAudioEngine.h"
#include <iostream>
#include <algorithm>

void data_callback(ma_device* pDevice, void* pOutput, const void* pInput, ma_uint32 frameCount) {
    RoneatAudioEngine* engine = (RoneatAudioEngine*)pDevice->pUserData;
    engine->processAudio((float*)pOutput, frameCount);
}

RoneatAudioEngine::RoneatAudioEngine() : isInitialized(false), m_sampleRate(44100), m_maxVoices(21) {
}

RoneatAudioEngine::~RoneatAudioEngine() {
    shutdown();
}

void RoneatAudioEngine::initialize(int sampleRate, int bufferSize) {
    if (isInitialized) {
        shutdown();
    }

    m_sampleRate = sampleRate;

    ma_device_config deviceConfig = ma_device_config_init(ma_device_type_playback);
    deviceConfig.playback.format   = ma_format_f32;
    deviceConfig.playback.channels = 1;
    deviceConfig.sampleRate        = sampleRate;
    deviceConfig.dataCallback      = data_callback;
    deviceConfig.pUserData         = this;
    deviceConfig.periodSizeInFrames = 128;
    deviceConfig.periods           = 2;

    if (ma_device_init(NULL, &deviceConfig, &device) != MA_SUCCESS) {
        std::cerr << "[C++] Failed to initialize playback device." << std::endl;
        return;
    }

    if (ma_device_start(&device) != MA_SUCCESS) {
        std::cerr << "[C++] Failed to start playback device." << std::endl;
        ma_device_uninit(&device);
        return;
    }

    isInitialized = true;
    std::cout << "[C++] RoneatAudioEngine initialized with sampleRate=" 
              << sampleRate << ", bufferSize=" << bufferSize << std::endl;
}

void RoneatAudioEngine::loadSampleFromBuffer(int barNumber, py::array_t<float> audioData) {
    std::lock_guard<std::mutex> lock(audioMutex);
    
    py::buffer_info buf = audioData.request();
    float* ptr = static_cast<float*>(buf.ptr);
    size_t size = buf.size;

    auto data = std::make_shared<std::vector<float>>(ptr, ptr + size);
    sampleLibrary[barNumber] = data;
    
    std::cout << "[C++] Loaded buffer for bar " << barNumber << " (" << size << " samples)" << std::endl;
}

void RoneatAudioEngine::playBuffer(py::array_t<float> audioData) {
    if (!isInitialized) return;
    
    py::buffer_info buf = audioData.request();
    float* ptr = static_cast<float*>(buf.ptr);
    size_t size = buf.size;

    auto data = std::make_shared<std::vector<float>>(ptr, ptr + size);

    std::lock_guard<std::mutex> lock(audioMutex);

    voices.erase(
        std::remove_if(voices.begin(), voices.end(), [](const Voice& v) { return !v.active; }),
        voices.end()
    );

    if (voices.size() >= m_maxVoices) {
        Voice* oldest_voice = nullptr;
        size_t max_played = 0;
        
        for (auto& v : voices) {
            if (!v.isFading && v.active && v.pos > max_played) {
                max_played = v.pos;
                oldest_voice = &v;
            }
        }
        
        if (oldest_voice != nullptr) {
            oldest_voice->isFading = true;
            oldest_voice->fadeStartPos = oldest_voice->pos;
            oldest_voice->fadeFrames = std::min((size_t)(m_sampleRate * 0.04), oldest_voice->data->size() - oldest_voice->pos);
            if (oldest_voice->fadeFrames == 0) {
                oldest_voice->active = false;
            }
        }
    }

    Voice newVoice;
    newVoice.noteId = -1; 
    newVoice.pos = 0;
    newVoice.isFading = false;
    newVoice.fadeStartPos = 0;
    newVoice.fadeFrames = 0;
    newVoice.active = true;
    newVoice.data = data;

    voices.push_back(newVoice);
}

void RoneatAudioEngine::triggerNote(int barNumber) {
    if (!isInitialized) return;

    std::lock_guard<std::mutex> lock(audioMutex);

    if (sampleLibrary.find(barNumber) == sampleLibrary.end()) {
        return; 
    }

    voices.erase(
        std::remove_if(voices.begin(), voices.end(), [](const Voice& v) { return !v.active; }),
        voices.end()
    );

    if (voices.size() >= m_maxVoices) {
        Voice* oldest_voice = nullptr;
        size_t max_played = 0;
        
        for (auto& v : voices) {
            if (!v.isFading && v.active && v.pos > max_played) {
                max_played = v.pos;
                oldest_voice = &v;
            }
        }
        
        if (oldest_voice != nullptr) {
            oldest_voice->isFading = true;
            oldest_voice->fadeStartPos = oldest_voice->pos;
            oldest_voice->fadeFrames = std::min((size_t)(m_sampleRate * 0.04), oldest_voice->data->size() - oldest_voice->pos);
            if (oldest_voice->fadeFrames == 0) {
                oldest_voice->active = false;
            }
        }
    }

    Voice newVoice;
    newVoice.noteId = barNumber;
    newVoice.pos = 0;
    newVoice.isFading = false;
    newVoice.fadeStartPos = 0;
    newVoice.fadeFrames = 0;
    newVoice.active = true;
    newVoice.data = sampleLibrary[barNumber];

    voices.push_back(newVoice);
}

void RoneatAudioEngine::stopAll() {
    std::lock_guard<std::mutex> lock(audioMutex);
    
    size_t default_fade_frames = (size_t)(m_sampleRate * 0.04);
    for (auto& v : voices) {
        if (!v.isFading && v.active && v.pos < v.data->size()) {
            v.isFading = true;
            v.fadeStartPos = v.pos;
            v.fadeFrames = std::min(default_fade_frames, v.data->size() - v.pos);
            if (v.fadeFrames == 0) {
                v.active = false;
            }
        }
    }
}

void RoneatAudioEngine::shutdown() {
    if (isInitialized) {
        ma_device_uninit(&device);
        isInitialized = false;
        std::cout << "[C++] RoneatAudioEngine shutdown called." << std::endl;
    }
}

void RoneatAudioEngine::processAudio(float* output, int frameCount) {
    std::lock_guard<std::mutex> lock(audioMutex);

    for (int i = 0; i < frameCount; ++i) {
        output[i] = 0.0f;
    }

    if (voices.empty()) return;

    for (auto& v : voices) {
        if (!v.active) continue;

        size_t rem = v.data->size() - v.pos;
        if (rem == 0) {
            v.active = false;
            continue;
        }

        size_t chunk = std::min((size_t)frameCount, rem);
        
        for (size_t i = 0; i < chunk; ++i) {
            float sample = (*v.data)[v.pos + i];
            
            if (v.isFading) {
                size_t fadePos = (v.pos + i) - v.fadeStartPos;
                if (fadePos >= v.fadeFrames) {
                    v.active = false;
                    break;
                }
                float fade_curve = 1.0f - ((float)fadePos / (float)v.fadeFrames);
                sample *= fade_curve;
            }
            
            output[i] += sample;
        }
        
        v.pos += chunk;

        if (v.pos >= v.data->size() && !v.isFading) {
            v.active = false;
        }
    }

    for (int i = 0; i < frameCount; ++i) {
        float val = output[i] * 0.75f;
        if (val > 1.0f) val = 1.0f;
        else if (val < -1.0f) val = -1.0f;
        output[i] = val;
    }
}
