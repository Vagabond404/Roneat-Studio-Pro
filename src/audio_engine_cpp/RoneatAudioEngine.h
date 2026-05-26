#pragma once

#ifndef NOMINMAX
#define NOMINMAX
#endif

#include <vector>
#include <unordered_map>
#include <string>
#include <mutex>
#include <memory>
#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>

#include "miniaudio.h"

namespace py = pybind11;

struct Voice {
    int noteId;
    std::shared_ptr<std::vector<float>> data;
    size_t pos;
    bool isFading;
    size_t fadeStartPos;
    size_t fadeFrames;
    bool active;
};

class RoneatAudioEngine {
public:
    RoneatAudioEngine();
    ~RoneatAudioEngine();

    void initialize(int sampleRate, int bufferSize);
    
    // Load a numpy array as the sound for a given note
    void loadSampleFromBuffer(int barNumber, py::array_t<float> audioData);
    
    // Play an arbitrary numpy array immediately
    void playBuffer(py::array_t<float> audioData);
    
    void triggerNote(int barNumber);
    void shutdown();
    void stopAll();

    // Internal callback
    void processAudio(float* output, int frameCount);

private:
    ma_device device;
    bool isInitialized;
    int m_sampleRate;
    int m_maxVoices;

    std::unordered_map<int, std::shared_ptr<std::vector<float>>> sampleLibrary;
    std::vector<Voice> voices;
    std::mutex audioMutex;
};
