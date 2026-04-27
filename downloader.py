"""
downloader.py – Core download engine wrapping yt-dlp.

Provides the VideoDownloader class with methods for:
  - Downloading videos at a chosen quality (4K / 1080p / 720p / 480p / 360p)
  - Extracting audio as MP3 or WAV
  - Fetching video metadata (title, thumbnail, available formats)
  - Batch downloading multiple URLs
  - Real-time progress callbacks for GUI / CLI integration
"""

import os
import re
import shutil
import subprocess
from pathlib import Path
import yt_dlp


# ── ffmpeg detection ─────────────────────────────────────────────────────────
HAS_FFMPEG = shutil.which("ffmpeg") is not None

# ── Quality presets ──────────────────────────────────────────────────────────
# When ffmpeg IS available we download separate video + audio streams and merge
# them (best quality). When ffmpeg is NOT available we fall back to pre-muxed
# single streams that don't require merging.
if HAS_FFMPEG:
    QUALITY_MAP = {
        "8K (4320p)":  "bestvideo[height<=4320][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=4320]+bestaudio/best[height<=4320]",
        "4K (2160p)":  "bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=2160]+bestaudio/best[height<=2160]",
        "1080p":       "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "720p":        "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]",
        "480p":        "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best[height<=480]",
        "360p":        "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=360]+bestaudio/best[height<=360]",
        "Best":        "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
    }
else:
    # Single pre-muxed streams – no ffmpeg needed
    QUALITY_MAP = {
        "8K (4320p)":  "best[height<=4320]",
        "4K (2160p)":  "best[height<=2160]",
        "1080p":       "best[height<=1080]",
        "720p":        "best[height<=720]",
        "480p":        "best[height<=480]",
        "360p":        "best[height<=360]",
        "Best":        "best",
    }

AUDIO_FORMATS = ("mp3", "wav")
CONTAINER_OPTIONS = ("Original", "mp4", "mkv")
CODEC_OPTIONS = (
    "Auto",
    "H.264 (AVC)",
    "H.265 (HEVC)",
    "AV1",
    "VP9",
)
FRAME_RATE_OPTIONS = ("Auto", "24", "30", "48", "60")

CODEC_FFMPEG_MAP = {
    "H.264 (AVC)": "libx264",
    "H.265 (HEVC)": "libx265",
    "AV1": "libaom-av1",
    "VP9": "libvpx-vp9",
}

PRESET_CONFIGS = {
    "MP4 (Universal)": {
        "quality": "4K (2160p)",
        "container": "mp4",
        "codec": "H.264 (AVC)",
        "frame_rate": "30",
    },
    "MKV (High Quality)": {
        "quality": "8K (4320p)",
        "container": "mkv",
        "codec": "H.265 (HEVC)",
        "frame_rate": "60",
    },
    "Android (Mobile Optimized)": {
        "quality": "720p",
        "container": "mp4",
        "codec": "H.264 (AVC)",
        "frame_rate": "30",
    },
    "Android Car LCD (Max Compatibility)": {
        "quality": "720p",
        "container": "mp4",
        "codec": "H.264 (AVC)",
        "frame_rate": "30",
    },
    "Linux (Open Codec)": {
        "quality": "4K (2160p)",
        "container": "mkv",
        "codec": "VP9",
        "frame_rate": "60",
    },
    "Windows (Playback Optimized)": {
        "quality": "4K (2160p)",
        "container": "mp4",
        "codec": "H.265 (HEVC)",
        "frame_rate": "60",
    },
}


def _sanitize_filename(name: str) -> str:
    """Remove characters that are unsafe in file paths."""
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()


class DownloadError(Exception):
    """Raised when a download fails for a known reason."""


class VideoDownloader:
    """High-level wrapper around yt-dlp for downloading YouTube videos/audio."""

    def __init__(
        self,
        output_dir: str = "downloads",
        progress_callback=None,
        log_callback=None,
    ):
        """
        Args:
            output_dir:         Folder where files are saved.
            progress_callback:  fn(percent: float, speed: str, eta: str) called on progress.
            log_callback:       fn(message: str) called for status messages.
        """
        self.output_dir = os.path.abspath(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        self._cancel_flag = False

    # ── Public API ───────────────────────────────────────────────────────

    def cancel(self):
        """Signal the current download to stop."""
        self._cancel_flag = True

    def reset_cancel(self):
        self._cancel_flag = False

    def get_video_info(self, url: str) -> dict:
        """
        Fetch metadata for a single YouTube video.

        Returns a dict with keys:
            title, thumbnail, duration, uploader, view_count, formats
        Raises DownloadError on failure.
        """
        opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except yt_dlp.utils.DownloadError as exc:
            raise DownloadError(self._friendly_error(str(exc))) from exc
        except Exception as exc:
            raise DownloadError(f"Failed to fetch info: {exc}") from exc

        # Reflect what this app can really download in the current environment.
        # Without ffmpeg we are limited to pre-muxed streams (video+audio in one).
        available_heights = self._collect_available_heights(info.get("formats", []))

        available_qualities = []
        for label, _ in QUALITY_MAP.items():
            # Parse the target height from the label
            if label == "Best":
                available_qualities.append(label)
            else:
                target = int(re.search(r"\d+", label).group())
                if any(h >= target for h in available_heights):
                    available_qualities.append(label)

        return {
            "title": info.get("title", "Unknown"),
            "thumbnail": info.get("thumbnail"),
            "duration": info.get("duration", 0),
            "uploader": info.get("uploader", "Unknown"),
            "view_count": info.get("view_count", 0),
            "available_qualities": available_qualities or ["Best"],
        }

    def download_video(
        self,
        url: str,
        quality: str = "Best",
        codec: str = "Auto",
        frame_rate: str = "Auto",
        container: str = "Original",
        preset_name: str | None = None,
    ) -> str:
        """
        Download a video at the given quality preset.

        Returns the path to the downloaded file.
        Raises DownloadError on failure.
        """
        self._cancel_flag = False

        config = {
            "quality": quality,
            "codec": codec,
            "frame_rate": frame_rate,
            "container": container,
            "preset_name": preset_name,
        }
        if preset_name:
            preset = PRESET_CONFIGS.get(preset_name)
            if not preset:
                raise DownloadError(
                    f"Unknown preset '{preset_name}'. Available: {list(PRESET_CONFIGS.keys())}"
                )
            config.update(preset)
            self._log(f"🎯 Preset selected: {preset_name} -> {preset}")

        self._validate_video_settings(
            quality=config["quality"],
            codec=config["codec"],
            frame_rate=config["frame_rate"],
            container=config["container"],
        )

        format_spec = QUALITY_MAP.get(config["quality"], QUALITY_MAP["Best"])

        if config["quality"] in ("4K (2160p)", "8K (4320p)") and not HAS_FFMPEG:
            raise DownloadError(
                "❌ 4K/8K download requires ffmpeg because YouTube usually provides high "
                "resolutions as separate video/audio streams.\n"
                "   Install it and restart the app:\n"
                "   winget install --id Gyan.FFmpeg -e"
            )

        if not HAS_FFMPEG and (
            config["codec"] != "Auto"
            or config["frame_rate"] != "Auto"
            or config["container"] != "Original"
        ):
            raise DownloadError(
                "❌ Codec/frame-rate/container customization requires ffmpeg.\n"
                "   Install it and restart the app:\n"
                "   winget install --id Gyan.FFmpeg -e"
            )

        if not HAS_FFMPEG:
            self._log("⚠  ffmpeg not found – using pre-muxed stream (quality may be limited).")

        opts = self._base_opts()
        opts.update({
            "format": format_spec,
            "outtmpl": os.path.join(
                self.output_dir, "%(title)s [%(resolution)s].%(ext)s"
            ),
        })
        # Only attempt merge when ffmpeg is present
        if HAS_FFMPEG:
            opts["merge_output_format"] = "mp4"

        filepath = self._run_download(url, opts, f"video ({config['quality']})")
        return self._smart_export(filepath, config)

    def extract_audio(self, url: str, audio_format: str = "mp3") -> str:
        """
        Download only the audio track and convert to *audio_format*.

        Returns the path to the saved audio file.
        Raises DownloadError on failure.
        """
        self._cancel_flag = False
        if audio_format not in AUDIO_FORMATS:
            raise DownloadError(
                f"Unsupported audio format '{audio_format}'. Use one of: {AUDIO_FORMATS}"
            )
        if not HAS_FFMPEG:
            raise DownloadError(
                "❌ ffmpeg is required for audio extraction but was not found.\n"
                "   Install it: winget install --id Gyan.FFmpeg -e\n"
                "   Or download from https://ffmpeg.org/download.html"
            )

        opts = self._base_opts()
        opts.update({
            "format": "bestaudio/best",
            "outtmpl": os.path.join(
                self.output_dir, "%(title)s.%(ext)s"
            ),
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": audio_format,
                    "preferredquality": "192" if audio_format == "mp3" else "0",
                }
            ],
        })

        return self._run_download(url, opts, f"audio ({audio_format})")

    def batch_download(
        self,
        urls: list[str],
        quality: str = "Best",
        audio_only: bool = False,
        audio_format: str = "mp3",
        codec: str = "Auto",
        frame_rate: str = "Auto",
        container: str = "Original",
        preset_name: str | None = None,
    ) -> list[dict]:
        """
        Download multiple URLs sequentially.

        Returns a list of dicts:  { url, success, path_or_error }
        """
        results = []
        for i, url in enumerate(urls, 1):
            url = url.strip()
            if not url:
                continue
            self._log(f"\n── [{i}/{len(urls)}]  {url}")
            try:
                if audio_only:
                    path = self.extract_audio(url, audio_format)
                else:
                    path = self.download_video(
                        url,
                        quality=quality,
                        codec=codec,
                        frame_rate=frame_rate,
                        container=container,
                        preset_name=preset_name,
                    )
                results.append({"url": url, "success": True, "path_or_error": path})
            except DownloadError as exc:
                results.append({"url": url, "success": False, "path_or_error": str(exc)})
            except Exception as exc:
                results.append({"url": url, "success": False, "path_or_error": str(exc)})

            if self._cancel_flag:
                self._log("⛔  Batch cancelled by user.")
                break

        return results

    # ── Internal helpers ─────────────────────────────────────────────────

    def _base_opts(self) -> dict:
        """Return common yt-dlp options shared by all download methods."""
        return {
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [self._progress_hook],
            "noprogress": False,
            "retries": 3,
            "fragment_retries": 3,
            "ignoreerrors": False,
            "noplaylist": True,
            "windowsfilenames": True,
        }

    def _run_download(self, url: str, opts: dict, label: str) -> str:
        """Execute the download and return the resulting filepath."""
        self._log(f"⬇  Starting {label} download …")
        self._last_filename = None

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info is None:
                    raise DownloadError("Download returned no data.")

                # Determine the filepath yt-dlp actually wrote
                filepath = info.get("requested_downloads", [{}])[0].get("filepath") \
                           or ydl.prepare_filename(info)
        except yt_dlp.utils.DownloadError as exc:
            raise DownloadError(self._friendly_error(str(exc))) from exc
        except DownloadError:
            raise
        except Exception as exc:
            raise DownloadError(f"Unexpected error: {exc}") from exc

        self._log(f"✅  Saved → {filepath}")
        return filepath

    def _validate_video_settings(
        self,
        quality: str,
        codec: str,
        frame_rate: str,
        container: str,
    ):
        if quality not in QUALITY_MAP:
            raise DownloadError(f"Unsupported quality '{quality}'.")
        if codec not in CODEC_OPTIONS:
            raise DownloadError(f"Unsupported codec '{codec}'.")
        if frame_rate not in FRAME_RATE_OPTIONS:
            raise DownloadError(f"Unsupported frame rate '{frame_rate}'.")
        if container not in CONTAINER_OPTIONS:
            raise DownloadError(f"Unsupported container '{container}'.")

    def _smart_export(self, filepath: str, config: dict) -> str:
        """Apply codec/frame-rate/container settings after download when needed."""
        codec = config["codec"]
        frame_rate = config["frame_rate"]
        container = config["container"]
        preset_name = config.get("preset_name")

        requires_processing = (
            codec != "Auto" or frame_rate != "Auto" or container != "Original"
        )
        if not requires_processing:
            return filepath

        if not HAS_FFMPEG:
            raise DownloadError("ffmpeg is required for export processing.")

        src = Path(filepath)
        target_ext = src.suffix if container == "Original" else f".{container}"
        dst = src.with_name(f"{src.stem} [export]{target_ext}")

        ffmpeg_codec = CODEC_FFMPEG_MAP.get(codec, "libx264")
        if codec == "Auto":
            ffmpeg_codec = "libx264"

        # Keep platform-friendly audio defaults per container.
        audio_codec = "aac" if target_ext.lower() == ".mp4" else "libopus"

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(src),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-c:v",
            ffmpeg_codec,
            "-c:a",
            audio_codec,
        ]

        if target_ext.lower() == ".mp4":
            # Use legacy-safe H.264/AAC settings for older Android/car LCD decoders.
            cmd.extend([
                "-movflags", "+faststart",
                "-pix_fmt", "yuv420p",
                "-c:v", "libx264",
                "-profile:v", "baseline",
                "-level", "3.1",
                "-vf", "scale=1280:-2:force_original_aspect_ratio=decrease",
                "-fps_mode", "cfr",
                "-c:a", "aac",
                "-b:a", "128k",
                "-ac", "2",
                "-ar", "44100",
                "-tag:v", "avc1",
            ])
            if preset_name != "Android Car LCD (Max Compatibility)":
                self._log("ℹ  MP4 compatibility mode enabled (Android/car safe).")

        if target_ext.lower() == ".mp4":
            cmd.extend(["-r", "30"])
        elif frame_rate != "Auto":
            cmd.extend(["-r", frame_rate])
        cmd.append(str(dst))

        self._log(
            f"🎬 Exporting with codec={codec}, fps={frame_rate}, container={target_ext.lstrip('.')} ..."
        )
        try:
            subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            err = (exc.stderr or exc.stdout or str(exc)).strip()
            raise DownloadError(f"Export failed: {err}") from exc

        try:
            src.unlink(missing_ok=True)
        except Exception:
            pass

        self._log(f"✅  Exported → {dst}")
        return str(dst)

    @staticmethod
    def _collect_available_heights(formats: list[dict]) -> set[int]:
        """Return heights that are realistically downloadable in this environment."""
        heights: set[int] = set()
        for fmt in formats:
            height = fmt.get("height")
            if not height:
                continue

            has_video = fmt.get("vcodec") not in (None, "none")
            has_audio = fmt.get("acodec") not in (None, "none")

            # With ffmpeg we can merge separate streams, so any video stream counts.
            if HAS_FFMPEG and has_video:
                heights.add(height)
            # Without ffmpeg only pre-muxed (video+audio) streams are downloadable.
            elif not HAS_FFMPEG and has_video and has_audio:
                heights.add(height)
        return heights

    def _progress_hook(self, d: dict):
        """Called by yt-dlp with download progress data."""
        if self._cancel_flag:
            raise yt_dlp.utils.DownloadError("Cancelled by user")

        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            percent = (downloaded / total * 100) if total else 0
            speed = d.get("_speed_str", "N/A")
            eta = d.get("_eta_str", "N/A")

            if self.progress_callback:
                self.progress_callback(percent, speed, eta)

        elif status == "finished":
            self._log("🔄  Merging / post-processing …")
            if self.progress_callback:
                self.progress_callback(100.0, "-", "-")

    def _log(self, message: str):
        """Send a log message to the caller."""
        if self.log_callback:
            self.log_callback(message)

    @staticmethod
    def _friendly_error(raw: str) -> str:
        """Convert common yt-dlp errors into user-friendly messages."""
        lower = raw.lower()
        if "private video" in lower or "sign in" in lower:
            return "❌ This video is private or requires sign-in."
        if "unavailable" in lower or "removed" in lower:
            return "❌ This video is unavailable or has been removed."
        if "age" in lower:
            return "❌ This video is age-restricted and cannot be downloaded without authentication."
        if "not a valid url" in lower or "unsupported url" in lower:
            return "❌ The URL provided is not a valid YouTube link."
        if "urlopen" in lower or "connection" in lower or "timed out" in lower:
            return "❌ Network error – check your internet connection and try again."
        if "copyright" in lower:
            return "❌ This video is blocked due to a copyright claim."
        return f"❌ Download failed: {raw}"
