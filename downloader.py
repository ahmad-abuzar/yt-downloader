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
import yt_dlp


# ── ffmpeg detection ─────────────────────────────────────────────────────────
HAS_FFMPEG = shutil.which("ffmpeg") is not None

# ── Quality presets ──────────────────────────────────────────────────────────
# When ffmpeg IS available we download separate video + audio streams and merge
# them (best quality). When ffmpeg is NOT available we fall back to pre-muxed
# single streams that don't require merging.
if HAS_FFMPEG:
    QUALITY_MAP = {
        "4K (2160p)":  "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
        "1080p":       "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "720p":        "bestvideo[height<=720]+bestaudio/best[height<=720]",
        "480p":        "bestvideo[height<=480]+bestaudio/best[height<=480]",
        "360p":        "bestvideo[height<=360]+bestaudio/best[height<=360]",
        "Best":        "bestvideo+bestaudio/best",
    }
else:
    # Single pre-muxed streams – no ffmpeg needed
    QUALITY_MAP = {
        "4K (2160p)":  "best[height<=2160]",
        "1080p":       "best[height<=1080]",
        "720p":        "best[height<=720]",
        "480p":        "best[height<=480]",
        "360p":        "best[height<=360]",
        "Best":        "best",
    }

AUDIO_FORMATS = ("mp3", "wav")


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

        # Determine the best available resolution
        available_heights = set()
        for fmt in info.get("formats", []):
            h = fmt.get("height")
            if h:
                available_heights.add(h)

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

    def download_video(self, url: str, quality: str = "Best") -> str:
        """
        Download a video at the given quality preset.

        Returns the path to the downloaded file.
        Raises DownloadError on failure.
        """
        self._cancel_flag = False
        format_spec = QUALITY_MAP.get(quality, QUALITY_MAP["Best"])

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

        return self._run_download(url, opts, f"video ({quality})")

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
                    path = self.download_video(url, quality)
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
