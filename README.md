# ⬇ YouTube Video Downloader

A feature-rich YouTube video downloader with a **modern dark-themed GUI** and **CLI** mode. Built with **yt-dlp** for reliable downloading and **CustomTkinter** for a sleek desktop experience.

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📹 Video Download | Up to **8K (4320p)** resolution |
| 🎵 Audio Extraction | Save as **MP3** or **WAV** |
| 📊 Quality Selector | 8K / 4K / 1080p / 720p / 480p / 360p / Best |
| 🎞️ Export Controls | Select **codec**, **frame rate**, and **container** independently |
| 🎯 Smart Presets | One-click presets for **MP4**, **MKV**, **Android**, **Linux**, **Windows** |
| 🚘 MP4 Compatibility Mode | All MP4 exports use Android-car-safe H.264/AAC defaults |
| 📦 Batch Download | Paste multiple URLs, one per line |
| 📈 Progress Tracking | Real-time progress bar, speed & ETA |
| ⛔ Cancel Support | Stop downloads mid-stream |
| 🛡️ Error Handling | Friendly messages for private, deleted, or age-restricted videos |

---

## 🚀 Installation

### 1. Prerequisites

- **Python 3.10+** – [Download](https://python.org/downloads)
- **ffmpeg** – Required for audio extraction & 4K merging

**Install ffmpeg on Windows:**
```bash
# Option A – winget
winget install --id Gyan.FFmpeg -e

# Option B – Download from https://ffmpeg.org/download.html
# Add the bin/ folder to your system PATH
```

### 2. Install Python dependencies

```bash
cd video_dlownloader
pip install -r requirements.txt
```

---

## 🖥️ Usage

### GUI Mode (default)

```bash
python main.py
```

This launches the graphical interface where you can:
1. Paste one or more YouTube URLs
2. Choose video quality or audio-only mode
3. Pick an output folder
4. Click **Fetch Info** to preview, then **Download**

### CLI Mode

```bash
# Download best quality
python main.py --cli --url "https://www.youtube.com/watch?v=VIDEO_ID"

# Download at 1080p
python main.py --cli --url "https://www.youtube.com/watch?v=VIDEO_ID" --quality "1080p"

# Smart preset export (auto quality/codec/fps/container)
python main.py --cli --url "https://www.youtube.com/watch?v=VIDEO_ID" --preset "Android (Mobile Optimized)"

# Android car LCD safe export (maximum compatibility)
python main.py --cli --url "https://www.youtube.com/watch?v=VIDEO_ID" --preset "Android Car LCD (Max Compatibility)"

# Manual export settings
python main.py --cli --url "https://www.youtube.com/watch?v=VIDEO_ID" --quality "8K (4320p)" --codec "H.265 (HEVC)" --frame-rate 60 --container mkv

# Extract audio as MP3
python main.py --cli --url "https://www.youtube.com/watch?v=VIDEO_ID" --audio

# Extract audio as WAV
python main.py --cli --url "https://www.youtube.com/watch?v=VIDEO_ID" --audio --audio-format wav

# Batch download multiple videos
python main.py --cli --url "URL1" --url "URL2" --url "URL3" --quality "720p"

# Custom output directory
python main.py --cli --url "URL" --output "./my_videos"
```

### CLI Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--cli` | Use command-line mode | GUI |
| `--url URL` | YouTube URL (repeatable) | — |
| `--quality Q` | Quality preset | `Best` |
| `--preset NAME` | Smart preset (overrides quality/codec/fps/container) | `None` |
| `--codec NAME` | Video codec (`Auto`, H.264, H.265, AV1, VP9) | `Auto` |
| `--frame-rate FPS` | Frame rate (`Auto`, 24, 30, 48, 60) | `Auto` |
| `--container C` | Output container (`Original`, `mp4`, `mkv`) | `Original` |
| `--audio` | Extract audio only | `False` |
| `--audio-format F` | `mp3` or `wav` | `mp3` |
| `--output DIR` | Output directory | `~/Downloads/YT_Downloads` |

---

## 📁 Project Structure

```
video_dlownloader/
├── main.py           # Entry point (CLI + GUI launcher)
├── app.py            # GUI application (CustomTkinter)
├── downloader.py     # Core download engine (yt-dlp wrapper)
├── requirements.txt  # Python dependencies
└── README.md         # This file
```

---

## ⚠️ Troubleshooting

| Error | Solution |
|-------|----------|
| `ffmpeg not found` | Install ffmpeg and add it to your PATH |
| `4K/8K or codec export failed` | Install ffmpeg (`winget install --id Gyan.FFmpeg -e`) |
| `Video not playing on Android car LCD` | Use preset `Android Car LCD (Max Compatibility)` |
| `Private video` | The video requires sign-in — not supported |
| `Age-restricted` | Cannot download without authentication |
| `Network error` | Check your internet connection |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |

---

## 📜 License

This project is for **personal and educational use only**. Respect YouTube's Terms of Service and content creators' rights.
