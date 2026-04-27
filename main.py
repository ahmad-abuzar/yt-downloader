"""
main.py – Entry point for the YouTube Video Downloader.

Usage:
    python main.py              → Launch the GUI (default)
    python main.py --cli        → Use the command-line mode

CLI examples:
    python main.py --cli --url "https://youtube.com/watch?v=..." --quality "1080p"
    python main.py --cli --url "https://youtube.com/watch?v=..." --audio --audio-format mp3
    python main.py --cli --url "URL1" --url "URL2" --quality "720p"
    python main.py --cli --url "URL" --output "./my_videos"
"""

import argparse
import sys
import os
import io

# Reconfigure stdout for UTF-8 on Windows to avoid cp1252 encoding errors
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )
        sys.stderr = io.TextIOWrapper(
            sys.stderr.buffer, encoding="utf-8", errors="replace"
        )

from downloader import (
    VideoDownloader,
    DownloadError,
    QUALITY_MAP,
    AUDIO_FORMATS,
    CODEC_OPTIONS,
    FRAME_RATE_OPTIONS,
    CONTAINER_OPTIONS,
    PRESET_CONFIGS,
)


def _cli_progress(percent: float, speed: str, eta: str):
    """Render a simple ASCII progress bar in the terminal."""
    bar_len = 40
    filled  = int(bar_len * percent / 100)
    bar     = "█" * filled + "░" * (bar_len - filled)
    sys.stdout.write(f"\r  [{bar}] {percent:5.1f}%  {speed}  ETA {eta}  ")
    sys.stdout.flush()
    if percent >= 100:
        sys.stdout.write("\n")


def _cli_log(message: str):
    print(message)


def run_cli(args: argparse.Namespace):
    """Execute a download from CLI arguments."""
    urls = args.url
    if not urls:
        print("❌  No URLs supplied. Use --url <URL> (repeatable).")
        sys.exit(1)

    output_dir = args.output or os.path.join(
        os.path.expanduser("~"), "Downloads", "YT_Downloads"
    )

    dl = VideoDownloader(
        output_dir=output_dir,
        progress_callback=_cli_progress,
        log_callback=_cli_log,
    )

    if args.audio:
        fmt = args.audio_format
        if fmt not in AUDIO_FORMATS:
            print(f"❌  Invalid audio format '{fmt}'. Choose from: {AUDIO_FORMATS}")
            sys.exit(1)
        results = dl.batch_download(urls, audio_only=True, audio_format=fmt)
    else:
        if args.preset and args.preset not in PRESET_CONFIGS:
            print(f"❌  Invalid preset '{args.preset}'. Choose from: {list(PRESET_CONFIGS.keys())}")
            sys.exit(1)

        quality = args.quality
        if quality not in QUALITY_MAP:
            print(f"❌  Invalid quality '{quality}'. Choose from: {list(QUALITY_MAP.keys())}")
            sys.exit(1)

        if args.codec not in CODEC_OPTIONS:
            print(f"❌  Invalid codec '{args.codec}'. Choose from: {list(CODEC_OPTIONS)}")
            sys.exit(1)

        if args.frame_rate not in FRAME_RATE_OPTIONS:
            print(
                f"❌  Invalid frame rate '{args.frame_rate}'. "
                f"Choose from: {list(FRAME_RATE_OPTIONS)}"
            )
            sys.exit(1)

        if args.container not in CONTAINER_OPTIONS:
            print(
                f"❌  Invalid container '{args.container}'. "
                f"Choose from: {list(CONTAINER_OPTIONS)}"
            )
            sys.exit(1)

        results = dl.batch_download(
            urls,
            quality=quality,
            codec=args.codec,
            frame_rate=args.frame_rate,
            container=args.container,
            preset_name=args.preset,
        )

    # Summary
    ok   = sum(1 for r in results if r["success"])
    fail = len(results) - ok
    print(f"\n{'═' * 40}")
    print(f"  ✅ {ok} succeeded   ❌ {fail} failed")
    print(f"{'═' * 40}")

    if fail:
        for r in results:
            if not r["success"]:
                print(f"  FAILED: {r['url']}\n         {r['path_or_error']}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="YouTube Video Downloader – download videos & audio from YouTube.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                                          Launch GUI
  python main.py --cli --url "https://youtu.be/abc123"    Download best quality
  python main.py --cli --url "URL" --quality "1080p"      Download at 1080p
  python main.py --cli --url "URL" --audio                Extract audio (MP3)
  python main.py --cli --url "URL" --audio --audio-format wav   Extract as WAV
  python main.py --cli --url "URL1" --url "URL2"          Batch download
        """,
    )
    parser.add_argument(
        "--cli", action="store_true",
        help="Run in command-line mode instead of launching the GUI.",
    )
    parser.add_argument(
        "--url", action="append", default=[],
        help="YouTube URL to download (can be repeated for batch).",
    )
    parser.add_argument(
        "--quality", default="Best",
        help=f"Video quality preset. Choices: {list(QUALITY_MAP.keys())}. Default: Best.",
    )
    parser.add_argument(
        "--preset", default=None,
        help=(
            f"Smart export preset name. Choices: {list(PRESET_CONFIGS.keys())}. "
            "When set, preset overrides quality/codec/frame-rate/container."
        ),
    )
    parser.add_argument(
        "--codec", default="Auto",
        help=f"Video codec. Choices: {list(CODEC_OPTIONS)}. Default: Auto.",
    )
    parser.add_argument(
        "--frame-rate", default="Auto", dest="frame_rate",
        help=f"Output frame rate. Choices: {list(FRAME_RATE_OPTIONS)}. Default: Auto.",
    )
    parser.add_argument(
        "--container", default="Original",
        help=f"Output container. Choices: {list(CONTAINER_OPTIONS)}. Default: Original.",
    )
    parser.add_argument(
        "--audio", action="store_true",
        help="Extract audio only.",
    )
    parser.add_argument(
        "--audio-format", default="mp3", dest="audio_format",
        help=f"Audio format when using --audio. Choices: {list(AUDIO_FORMATS)}. Default: mp3.",
    )
    parser.add_argument(
        "--output", default=None,
        help="Output directory. Default: ~/Downloads/YT_Downloads.",
    )

    args = parser.parse_args()

    if args.cli:
        run_cli(args)
    else:
        from app import launch
        launch()


if __name__ == "__main__":
    main()
