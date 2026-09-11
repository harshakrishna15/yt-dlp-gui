import io
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from gui.common import download, media_probe
from gui.common.yt_dlp_cli import MetadataCancelled


def compatible_info():
    return {"streams": [
        {"index": 0, "codec_type": "video", "codec_name": "h264", "profile": "High",
         "level": 41, "pix_fmt": "yuv420p", "width": 1920, "height": 1080,
         "field_order": "progressive", "avg_frame_rate": "30/1", "r_frame_rate": "30/1",
         "time_base": "1/15360"},
        {"codec_type": "audio", "codec_name": "aac", "profile": "LC", "sample_rate": "48000"},
    ], "format": {"duration": "10"}}


class TestMediaProbe(unittest.TestCase):
    def test_stream_compatibility_is_conservative(self):
        self.assertIsNotNone(media_probe.compatible_streams(compatible_info()))
        for key, value in [("pix_fmt", "yuv420p10le"), ("codec_name", "hevc"),
                           ("width", 1919), ("field_order", "tt"), ("level", 51),
                           ("avg_frame_rate", "29/1"), ("color_transfer", "smpte2084")]:
            info = compatible_info()
            info["streams"][0][key] = value
            self.assertIsNone(media_probe.compatible_streams(info), key)
        info = compatible_info()
        info["streams"][1]["sample_rate"] = "44100"
        self.assertIsNone(media_probe.compatible_streams(info))
        self.assertIsNone(media_probe.compatible_streams({}))

    def test_packet_timing_is_checked_not_just_average_rate(self):
        def check(xml):
            with patch.object(media_probe, "_probe", side_effect=lambda b, p, a, e, consume: consume(io.BytesIO(xml))):
                return media_probe.is_edit_compatible(Path("video.mp4"), Path("ffprobe"), compatible_info())
        self.assertTrue(check(b'<ffprobe><packets><packet dts="-512" duration="512"/><packet dts="0" duration="512"/></packets></ffprobe>'))
        self.assertFalse(check(b'<ffprobe><packets><packet dts="0" duration="512"/><packet dts="1024" duration="512"/></packets></ffprobe>'))
        self.assertFalse(check(b'<ffprobe><packets><packet dts="0" duration="256"/></packets></ffprobe>'))
        self.assertFalse(check(b'<ffprobe><packets><packet/></packets></ffprobe>'))

    def test_probe_cancelled_before_spawn(self):
        event = threading.Event()
        event.set()
        with patch.object(media_probe.subprocess, "Popen") as spawn:
            with self.assertRaises(MetadataCancelled):
                media_probe.probe_media(Path("video.mp4"), Path("ffprobe"), event)
        spawn.assert_not_called()

    def test_compatible_mp4_never_starts_encoder(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "video.mp4"
            path.touch()
            with patch.object(download, "resolve_binary", return_value=(Path("tool"), "test")), patch.object(
                media_probe, "probe_media", return_value=compatible_info()
            ), patch.object(media_probe, "is_edit_compatible", return_value=True), patch.object(
                download, "_select_edit_friendly_video_codec"
            ) as select, patch.object(download, "_reencode_edit_friendly_mp4_file") as encode:
                download._postprocess_edit_friendly_mp4(
                    output_paths=[path], format_filter="mp4", fmt_info=None,
                    edit_friendly_encoder="auto", cancel_event=None,
                    log=lambda _: None, update_progress=lambda _: None,
                )
            select.assert_not_called()
            encode.assert_not_called()
