#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include "RoneatAudioEngine.h"

namespace py = pybind11;

PYBIND11_MODULE(roneat_audio_core, m) {
    m.doc() = "Roneat Studio Pro core audio engine C++ bindings";

    py::class_<RoneatAudioEngine>(m, "RoneatAudioEngine")
        .def(py::init<>())
        .def("initialize", &RoneatAudioEngine::initialize, "Initialize the audio engine")
        .def("loadSampleFromBuffer", &RoneatAudioEngine::loadSampleFromBuffer, "Load an audio sample array for a bar")
        .def("playBuffer", &RoneatAudioEngine::playBuffer, "Play an arbitrary float32 numpy array immediately")
        .def("triggerNote", &RoneatAudioEngine::triggerNote, "Trigger a note")
        .def("stopAll", &RoneatAudioEngine::stopAll, "Stop all active notes")
        .def("shutdown", &RoneatAudioEngine::shutdown, "Shutdown the audio engine");
}
