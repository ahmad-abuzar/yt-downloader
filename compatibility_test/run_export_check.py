import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from downloader import VideoDownloader


dl = VideoDownloader(output_dir="compatibility_test", log_callback=print)
config = {
    "quality": "1080p",
    "codec": "Auto",
    "frame_rate": "Auto",
    "container": "mp4",
    "preset_name": None,
}

out = dl._smart_export("compatibility_test/input_hevc.mp4", config)
print(f"EXPORT_OUTPUT={out}")
