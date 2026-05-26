#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include "RoneatVideoEngine.h"

namespace py = pybind11;

PYBIND11_MODULE(roneat_video_core, m) {
    m.doc() = "Roneat Studio Pro core video engine C++ bindings";

    py::class_<VideoEvent>(m, "VideoEvent")
        .def(py::init<double, double, std::optional<int>, std::optional<int>, bool, int, int>(),
             py::arg("t_start"), py::arg("duration"), py::arg("bar"), 
             py::arg("left_bar") = std::nullopt, py::arg("is_tremolo_hit") = false, 
             py::arg("sub_hit") = 0, py::arg("total_hits") = 1)
        .def_readwrite("t_start", &VideoEvent::t_start)
        .def_readwrite("duration", &VideoEvent::duration)
        .def_readwrite("bar", &VideoEvent::bar)
        .def_readwrite("left_bar", &VideoEvent::left_bar)
        .def_readwrite("is_tremolo_hit", &VideoEvent::is_tremolo_hit)
        .def_readwrite("sub_hit", &VideoEvent::sub_hit)
        .def_readwrite("total_hits", &VideoEvent::total_hits);

    py::class_<RoneatVideoEngine>(m, "RoneatVideoEngine")
        .def(py::init<>())
        .def("build_timeline", &RoneatVideoEngine::build_timeline, 
             py::arg("score_text"), py::arg("bpm"), py::arg("hits_per_sec"), 
             py::arg("sync_data") = py::none(), py::arg("tail_sec") = 2.0,
             "Build timeline of events")
        .def("render_frame", &RoneatVideoEngine::render_frame,
             py::arg("active_bar"), py::arg("active_left_bar"), py::arg("frame_t"), py::arg("event_t"), py::arg("event_dur"),
             py::arg("W") = 1920, py::arg("H") = 1080, py::arg("dark_mode") = true,
             py::arg("song_title") = "", py::arg("two_mallets") = true, py::arg("accent_hex") = "#c8a96e",
             py::arg("view_mode") = "Numeric", py::arg("is_tremolo_hit") = false, py::arg("sub_hit") = 0, py::arg("total_hits") = 1,
             py::arg("title_scale") = 1.0, py::arg("label_scale") = 1.0, py::arg("status_scale") = 1.0,
             py::arg("title_y_offset") = 0.0, py::arg("label_y_offset") = 0.0, py::arg("status_y_offset") = 0.0,
             py::arg("show_labels") = true, py::arg("show_status") = true, py::arg("font_path") = "Arial.ttf",
             py::arg("title_img") = py::none(),
             "Render frame of video. active_left_bar determines the left mallet strike bar index.")
        .def("export_mp4", &RoneatVideoEngine::export_mp4,
             py::arg("filepath"), py::arg("score_text"), py::arg("bpm"), py::arg("hits_per_sec"),
             py::arg("audio_arr"), py::arg("audio_rate"), py::arg("dark_mode") = true,
             py::arg("song_title") = "", py::arg("two_mallets") = true, py::arg("accent_hex") = "#c8a96e",
             py::arg("view_mode") = "Numeric", py::arg("sync_data") = py::none(), py::arg("ffmpeg_bin") = "ffmpeg",
             py::arg("progress_cb") = py::none(), py::arg("W") = 1920, py::arg("H") = 1080, py::arg("FPS") = 60,
             py::arg("title_scale") = 1.0, py::arg("label_scale") = 1.0, py::arg("status_scale") = 1.0,
             py::arg("title_y_offset") = 0.0, py::arg("label_y_offset") = 0.0, py::arg("status_y_offset") = 0.0,
             py::arg("show_labels") = true, py::arg("show_status") = true, py::arg("font_path") = "Arial.ttf",
             py::arg("title_img") = py::none(),
             "Export MP4 video");
}
