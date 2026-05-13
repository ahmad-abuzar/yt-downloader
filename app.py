"""
app.py – Modern dark-themed GUI for the YouTube Video Downloader.

Built with CustomTkinter for a sleek, native-feeling desktop experience.
Features:
  • URL text area (single or batch, one per line)
  • Quality selector (4K / 1080p / 720p / 480p / 360p / Best)
  • Audio-only mode with format selector (MP3 / WAV)
  • Output folder picker
  • Fetch Info – preview title before downloading
  • Real-time progress bar + scrollable log
  • Cancel button
"""

import os
import threading
import tkinter as tk
from datetime import timedelta

import customtkinter as ctk

from downloader import (
    VideoDownloader,
    DownloadError,
    QUALITY_MAP,
    AUDIO_FORMATS,
    CODEC_OPTIONS,
    FRAME_RATE_OPTIONS,
    CONTAINER_OPTIONS,
    CONVERSION_RESOLUTION_OPTIONS,
    PRESET_CONFIGS,
    HAS_FFMPEG,
)


# ── Theme ────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Colour palette
BG_DARK       = "#0f0f0f"
CARD_BG       = "#1a1a2e"
ACCENT         = "#e94560"
ACCENT_HOVER   = "#ff6b81"
TEXT_PRIMARY   = "#eaeaea"
TEXT_SECONDARY = "#a0a0b0"
SUCCESS        = "#2ecc71"
WARNING        = "#f39c12"
BORDER         = "#2a2a3e"


class App(ctk.CTk):
    """Main application window."""

    WIDTH  = 900
    HEIGHT = 720

    def __init__(self):
        super().__init__()

        # ── Window setup ─────────────────────────────────────────────────
        self.title("⬇  YouTube Video Downloader")
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self.minsize(640, 540)
        self.configure(fg_color=BG_DARK)

        self._download_thread: threading.Thread | None = None
        self._downloader: VideoDownloader | None = None
        self._operation_active = False
        self.quality_options = list(QUALITY_MAP.keys())
        if not HAS_FFMPEG:
            self.quality_options = [
                q for q in self.quality_options if q not in {"4K (2160p)", "8K (4320p)"}
            ]

        self._build_ui()
        self.after(150, self._log_ffmpeg_hint)

    # ══════════════════════════════════════════════════════════════════════
    #  UI Construction
    # ══════════════════════════════════════════════════════════════════════

    def _build_ui(self):
        # Scrollable main container so the full app stays reachable on small screens
        self.main = ctk.CTkScrollableFrame(
            self,
            fg_color=BG_DARK,
            corner_radius=0,
            scrollbar_button_color=ACCENT,
            scrollbar_button_hover_color=ACCENT_HOVER,
        )
        self.main.pack(fill="both", expand=True, padx=12, pady=12)

        self._build_header()
        self._build_url_section()
        self._build_options_section()
        self._build_output_section()
        self._build_action_buttons()
        self._build_converter_section()
        self._build_progress_section()
        self._build_log_section()

    # ── Header ───────────────────────────────────────────────────────────
    def _build_header(self):
        header = ctk.CTkFrame(self.main, fg_color="transparent")
        header.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            header,
            text="⬇  YouTube Video Downloader",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(side="left")

        ctk.CTkLabel(
            header,
            text="powered by yt-dlp",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_SECONDARY,
        ).pack(side="left", padx=(10, 0), pady=(8, 0))

    # ── URL input ────────────────────────────────────────────────────────
    def _build_url_section(self):
        card = self._card(self.main)

        ctk.CTkLabel(
            card,
            text="🔗  YouTube URL(s)  –  one per line for batch downloads",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w", pady=(0, 6))

        self.url_textbox = ctk.CTkTextbox(
            card,
            height=90,
            font=ctk.CTkFont(size=13),
            fg_color="#12121f",
            border_color=BORDER,
            border_width=1,
            corner_radius=8,
            text_color=TEXT_PRIMARY,
        )
        self.url_textbox.pack(fill="x")

    # ── Options (Presets / Quality / Codec / FPS / Audio) ─────────────────
    def _build_options_section(self):
        card = self._card(self.main)
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            top,
            text="🎯  Export Preset",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXT_SECONDARY,
        ).pack(side="left")

        self.preset_var = ctk.StringVar(value="Custom (Manual)")
        self.preset_menu = ctk.CTkOptionMenu(
            top,
            variable=self.preset_var,
            values=["Custom (Manual)", *PRESET_CONFIGS.keys()],
            width=280,
            fg_color="#12121f",
            button_color=ACCENT,
            button_hover_color=ACCENT_HOVER,
            corner_radius=8,
            command=self._on_preset_change,
        )
        self.preset_menu.pack(side="left", padx=(10, 0))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x")

        # Quality + container
        left = ctk.CTkFrame(row, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            left, text="📺  Video Quality",
            font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_SECONDARY,
        ).pack(anchor="w", pady=(0, 4))
        self.quality_var = ctk.StringVar(value="Best")
        self.quality_menu = ctk.CTkOptionMenu(
            left,
            variable=self.quality_var,
            values=self.quality_options,
            width=200,
            fg_color="#12121f",
            button_color=ACCENT,
            button_hover_color=ACCENT_HOVER,
            corner_radius=8,
        )
        self.quality_menu.pack(anchor="w")

        ctk.CTkLabel(
            left, text="📦  Container",
            font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_SECONDARY,
        ).pack(anchor="w", pady=(8, 4))
        self.container_var = ctk.StringVar(value="Original")
        self.container_menu = ctk.CTkOptionMenu(
            left,
            variable=self.container_var,
            values=list(CONTAINER_OPTIONS),
            width=200,
            fg_color="#12121f",
            button_color=ACCENT,
            button_hover_color=ACCENT_HOVER,
            corner_radius=8,
        )
        self.container_menu.pack(anchor="w")

        # Codec + fps + audio
        right = ctk.CTkFrame(row, fg_color="transparent")
        right.pack(side="right", padx=(20, 0))

        ctk.CTkLabel(
            right, text="🎞  Video Codec",
            font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_SECONDARY,
        ).pack(anchor="w", pady=(0, 4))
        self.codec_var = ctk.StringVar(value="Auto")
        self.codec_menu = ctk.CTkOptionMenu(
            right,
            variable=self.codec_var,
            values=list(CODEC_OPTIONS),
            width=220,
            fg_color="#12121f",
            button_color=ACCENT,
            button_hover_color=ACCENT_HOVER,
            corner_radius=8,
        )
        self.codec_menu.pack(anchor="w")

        ctk.CTkLabel(
            right, text="⏱  Frame Rate",
            font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_SECONDARY,
        ).pack(anchor="w", pady=(8, 4))
        self.frame_rate_var = ctk.StringVar(value="Auto")
        self.frame_rate_menu = ctk.CTkOptionMenu(
            right,
            variable=self.frame_rate_var,
            values=list(FRAME_RATE_OPTIONS),
            width=220,
            fg_color="#12121f",
            button_color=ACCENT,
            button_hover_color=ACCENT_HOVER,
            corner_radius=8,
        )
        self.frame_rate_menu.pack(anchor="w")

        self.audio_only_var = ctk.BooleanVar(value=False)
        self.audio_check = ctk.CTkCheckBox(
            right,
            text="🎵  Audio only",
            variable=self.audio_only_var,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXT_SECONDARY,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            corner_radius=6,
            command=self._on_audio_toggle,
        )
        self.audio_check.pack(anchor="w", pady=(10, 4))

        self.audio_format_var = ctk.StringVar(value="mp3")
        self.audio_format_menu = ctk.CTkOptionMenu(
            right,
            variable=self.audio_format_var,
            values=list(AUDIO_FORMATS),
            width=120,
            fg_color="#12121f",
            button_color=ACCENT,
            button_hover_color=ACCENT_HOVER,
            corner_radius=8,
            state="disabled",
        )
        self.audio_format_menu.pack(anchor="w")

        self._sync_video_controls_state()

    # ── Output folder ────────────────────────────────────────────────────
    def _build_output_section(self):
        card = self._card(self.main)
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x")

        ctk.CTkLabel(
            row, text="📁  Output Folder",
            font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_SECONDARY,
        ).pack(side="left", pady=(0, 0))

        self.output_var = ctk.StringVar(
            value=os.path.join(os.path.expanduser("~"), "Downloads", "YT_Downloads")
        )
        self.output_entry = ctk.CTkEntry(
            row,
            textvariable=self.output_var,
            font=ctk.CTkFont(size=13),
            fg_color="#12121f",
            border_color=BORDER,
            border_width=1,
            corner_radius=8,
            text_color=TEXT_PRIMARY,
            width=420,
        )
        self.output_entry.pack(side="left", padx=(12, 8), fill="x", expand=True)

        ctk.CTkButton(
            row, text="Browse", width=90,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, corner_radius=8,
            command=self._browse_folder,
        ).pack(side="right")

    # ── Converter ───────────────────────────────────────────────────────
    def _build_converter_section(self):
        card = self._card(self.main)

        ctk.CTkLabel(
            card,
            text="🎬  Video Converter  –  convert a local video to 720p / 1080p / 4K",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w", pady=(0, 8))

        file_row = ctk.CTkFrame(card, fg_color="transparent")
        file_row.pack(fill="x", pady=(0, 8))

        self.convert_source_var = ctk.StringVar(value="")
        self.convert_source_entry = ctk.CTkEntry(
            file_row,
            textvariable=self.convert_source_var,
            font=ctk.CTkFont(size=13),
            fg_color="#12121f",
            border_color=BORDER,
            border_width=1,
            corner_radius=8,
            text_color=TEXT_PRIMARY,
        )
        self.convert_source_entry.pack(side="left", fill="x", expand=True)

        ctk.CTkButton(
            file_row,
            text="Browse File",
            width=110,
            fg_color="#1e3a5f",
            hover_color="#264d73",
            corner_radius=8,
            command=self._browse_convert_source,
        ).pack(side="left", padx=(8, 0))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x")

        left = ctk.CTkFrame(row, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            left,
            text="Target Resolution",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w", pady=(0, 4))

        self.convert_resolution_var = ctk.StringVar(value="1080p")
        self.convert_resolution_menu = ctk.CTkOptionMenu(
            left,
            variable=self.convert_resolution_var,
            values=list(CONVERSION_RESOLUTION_OPTIONS),
            width=200,
            fg_color="#12121f",
            button_color=ACCENT,
            button_hover_color=ACCENT_HOVER,
            corner_radius=8,
        )
        self.convert_resolution_menu.pack(anchor="w")

        self.convert_keep_source_var = ctk.BooleanVar(value=True)
        self.convert_keep_source_check = ctk.CTkCheckBox(
            left,
            text="Keep source file",
            variable=self.convert_keep_source_var,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXT_SECONDARY,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            corner_radius=6,
        )
        self.convert_keep_source_check.pack(anchor="w", pady=(10, 0))

        right = ctk.CTkFrame(row, fg_color="transparent")
        right.pack(side="right", padx=(20, 0))

        ctk.CTkLabel(
            right,
            text="Container",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w", pady=(0, 4))

        self.convert_container_var = ctk.StringVar(value="mp4")
        self.convert_container_menu = ctk.CTkOptionMenu(
            right,
            variable=self.convert_container_var,
            values=list(CONTAINER_OPTIONS),
            width=170,
            fg_color="#12121f",
            button_color=ACCENT,
            button_hover_color=ACCENT_HOVER,
            corner_radius=8,
        )
        self.convert_container_menu.pack(anchor="w")

        ctk.CTkLabel(
            right,
            text="Codec",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w", pady=(8, 4))

        self.convert_codec_var = ctk.StringVar(value="Auto")
        self.convert_codec_menu = ctk.CTkOptionMenu(
            right,
            variable=self.convert_codec_var,
            values=list(CODEC_OPTIONS),
            width=170,
            fg_color="#12121f",
            button_color=ACCENT,
            button_hover_color=ACCENT_HOVER,
            corner_radius=8,
        )
        self.convert_codec_menu.pack(anchor="w")

        self.convert_btn = ctk.CTkButton(
            card,
            text="🔄  Convert Video",
            width=180,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            corner_radius=10,
            command=self._on_convert,
        )
        self.convert_btn.pack(anchor="e", pady=(10, 0))

    # ── Action buttons ───────────────────────────────────────────────────
    def _build_action_buttons(self):
        row = ctk.CTkFrame(self.main, fg_color="transparent")
        row.pack(fill="x", pady=(10, 6))

        self.fetch_btn = ctk.CTkButton(
            row, text="🔍  Fetch Info", width=150,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#1e3a5f", hover_color="#264d73", corner_radius=10,
            command=self._on_fetch_info,
        )
        self.fetch_btn.pack(side="left")

        self.download_btn = ctk.CTkButton(
            row, text="⬇  Download", width=180,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=ACCENT, hover_color=ACCENT_HOVER, corner_radius=10,
            command=self._on_download,
        )
        self.download_btn.pack(side="left", padx=(12, 0))

        self.cancel_btn = ctk.CTkButton(
            row, text="⛔  Cancel", width=120,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#555", hover_color="#777", corner_radius=10,
            state="disabled",
            command=self._on_cancel,
        )
        self.cancel_btn.pack(side="left", padx=(12, 0))

        self.open_folder_btn = ctk.CTkButton(
            row, text="📂  Open Folder", width=140,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#1e3a5f", hover_color="#264d73", corner_radius=10,
            command=self._open_output_folder,
        )
        self.open_folder_btn.pack(side="right")

    # ── Progress bar ─────────────────────────────────────────────────────
    def _build_progress_section(self):
        card = self._card(self.main)

        info_row = ctk.CTkFrame(card, fg_color="transparent")
        info_row.pack(fill="x", pady=(0, 4))
        self.progress_label = ctk.CTkLabel(
            info_row, text="Ready", font=ctk.CTkFont(size=12),
            text_color=TEXT_SECONDARY,
        )
        self.progress_label.pack(side="left")
        self.speed_label = ctk.CTkLabel(
            info_row, text="", font=ctk.CTkFont(size=12),
            text_color=TEXT_SECONDARY,
        )
        self.speed_label.pack(side="right")

        self.progress_bar = ctk.CTkProgressBar(
            card, width=400, height=14,
            fg_color="#12121f",
            progress_color=ACCENT,
            corner_radius=7,
        )
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x")

    # ── Log area ─────────────────────────────────────────────────────────
    def _build_log_section(self):
        card = self._card(self.main, expand=True)

        ctk.CTkLabel(
            card, text="📋  Log",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w", pady=(0, 4))

        # Create a frame to hold the textbox and its vertical scrollbar
        log_frame = ctk.CTkFrame(card, fg_color="transparent")
        log_frame.pack(fill="both", expand=True)

        self.log_textbox = ctk.CTkTextbox(
            log_frame, font=ctk.CTkFont(family="Consolas", size=12),
            fg_color="#0b0b14", corner_radius=8,
            text_color="#c8c8d8", state="normal", wrap="none",
        )
        self.log_textbox.pack(side="left", fill="both", expand=True)

        # Vertical scrollbar for the log area
        self.log_scrollbar = ctk.CTkScrollbar(log_frame, orientation="vertical")
        self.log_scrollbar.pack(side="right", fill="y")

        # Wire the scrollbar and textbox together
        try:
            self.log_textbox.configure(yscrollcommand=self.log_scrollbar.set)
            self.log_scrollbar.configure(command=self.log_textbox.yview)
        except Exception:
            # Fallback: some CTk versions wrap differently; ignore if not supported
            pass

        self.log_textbox.configure(state="disabled")

    def _log_ffmpeg_hint(self):
        if not HAS_FFMPEG:
            self._log(
                "⚠  ffmpeg not detected. 4K/8K and codec/fps export controls are limited.\n"
                "   Install: winget install --id Gyan.FFmpeg -e"
            )

    # ══════════════════════════════════════════════════════════════════════
    #  Event handlers
    # ══════════════════════════════════════════════════════════════════════

    def _on_audio_toggle(self):
        self._sync_video_controls_state()

    def _on_preset_change(self, selected: str):
        if selected == "Custom (Manual)":
            self._log("🛠  Manual export mode enabled.")
            self._sync_video_controls_state()
            return

        preset = PRESET_CONFIGS.get(selected)
        if not preset:
            return

        if preset["quality"] in self.quality_options:
            self.quality_var.set(preset["quality"])
        else:
            self.quality_var.set("Best")
        self.codec_var.set(preset["codec"])
        self.frame_rate_var.set(preset["frame_rate"])
        self.container_var.set(preset["container"])
        self._log(
            f"🎯 Preset applied: {selected} -> quality={self.quality_var.get()}, "
            f"codec={self.codec_var.get()}, fps={self.frame_rate_var.get()}, "
            f"container={self.container_var.get()}"
        )
        self._sync_video_controls_state()

    def _sync_video_controls_state(self):
        audio_only = self.audio_only_var.get()
        preset_selected = self.preset_var.get() != "Custom (Manual)"

        self.audio_format_menu.configure(state="normal" if audio_only else "disabled")

        video_state = "disabled" if audio_only or preset_selected else "normal"
        self.quality_menu.configure(state=video_state)
        self.codec_menu.configure(state=video_state)
        self.frame_rate_menu.configure(state=video_state)
        self.container_menu.configure(state=video_state)

    def _browse_folder(self):
        folder = ctk.filedialog.askdirectory()
        if folder:
            self.output_var.set(folder)

    def _open_output_folder(self):
        folder = self.output_var.get()
        if os.path.isdir(folder):
            os.startfile(folder)
        else:
            self._log("⚠  Output folder does not exist yet.")

    def _on_fetch_info(self):
        if self._operation_active:
            self._log("⚠  Please wait for the current task to finish.")
            return
        urls = self._get_urls()
        if not urls:
            self._log("⚠  Please paste at least one YouTube URL.")
            return
        self._set_busy(True, label="Fetching info …")
        threading.Thread(target=self._fetch_info_worker, args=(urls,), daemon=True).start()

    def _fetch_info_worker(self, urls: list[str]):
        try:
            dl = VideoDownloader(output_dir=self.output_var.get())
            for url in urls:
                try:
                    info = dl.get_video_info(url)
                    dur = str(timedelta(seconds=info["duration"])) if info["duration"] else "N/A"
                    views = f'{info["view_count"]:,}' if info["view_count"] else "N/A"
                    qualities = ", ".join(info["available_qualities"])
                    self._log(
                        f"────────────────────────────────\n"
                        f"📹  {info['title']}\n"
                        f"   👤 {info['uploader']}   ⏱ {dur}   👀 {views}\n"
                        f"   Available: {qualities}\n"
                    )
                except DownloadError as exc:
                    self._log(f"{exc}")
                except Exception as exc:
                    self._log(f"❌ Error: {exc}")
        except Exception as exc:
            self._log(f"❌ Error: {exc}")
        finally:
            self.after(0, lambda: self._set_busy(False))

    def _on_download(self):
        if self._operation_active:
            self._log("⚠  Please wait for the current task to finish.")
            return
        urls = self._get_urls()
        if not urls:
            self._log("⚠  Please paste at least one YouTube URL.")
            return
        self._set_busy(True, label="Downloading …")
        self._download_thread = threading.Thread(
            target=self._download_worker, args=(urls,), daemon=True
        )
        self._download_thread.start()

    def _browse_convert_source(self):
        file_path = ctk.filedialog.askopenfilename(
            title="Select a video file to convert",
            filetypes=[
                ("Video files", "*.mp4 *.mkv *.webm *.mov *.avi *.m4v *.flv"),
                ("All files", "*.*"),
            ],
        )
        if file_path:
            self.convert_source_var.set(file_path)

    def _on_convert(self):
        if self._operation_active:
            self._log("⚠  Please wait for the current task to finish.")
            return

        source = self.convert_source_var.get().strip()
        if not source:
            self._log("⚠  Please choose a video file to convert.")
            return

        self._set_busy(True, label="Converting …")
        threading.Thread(target=self._convert_worker, daemon=True).start()

    def _convert_worker(self):
        try:
            converter = VideoDownloader(output_dir=self.output_var.get(), log_callback=self._log)
            result = converter.convert_video_file(
                self.convert_source_var.get().strip(),
                output_dir=self.output_var.get(),
                target_resolution=self.convert_resolution_var.get(),
                codec=self.convert_codec_var.get(),
                container=self.convert_container_var.get(),
                keep_source=self.convert_keep_source_var.get(),
            )
            self._log(f"✅  Converted file saved at: {result}")
        except DownloadError as exc:
            self._log(str(exc))
        except Exception as exc:
            self._log(f"❌ Error: {exc}")
        finally:
            self.after(0, lambda: self._set_busy(False))

    def _download_worker(self, urls: list[str]):
        try:
            self._downloader = VideoDownloader(
                output_dir=self.output_var.get(),
                progress_callback=self._on_progress,
                log_callback=self._log,
            )

            audio_only = self.audio_only_var.get()
            audio_fmt  = self.audio_format_var.get()
            quality    = self.quality_var.get()
            codec      = self.codec_var.get()
            frame_rate = self.frame_rate_var.get()
            container  = self.container_var.get()
            preset     = self.preset_var.get()
            preset_name = None if preset == "Custom (Manual)" else preset

            results = self._downloader.batch_download(
                urls,
                quality=quality,
                audio_only=audio_only,
                audio_format=audio_fmt,
                codec=codec,
                frame_rate=frame_rate,
                container=container,
                preset_name=preset_name,
            )

            # Summary
            ok = sum(1 for r in results if r["success"])
            fail = len(results) - ok
            self._log(
                f"\n═══════════════════════════════\n"
                f"  ✅ {ok} succeeded   ❌ {fail} failed\n"
                f"═══════════════════════════════"
            )
        except Exception as exc:
            self._log(f"❌ Error: {exc}")
        finally:
            self.after(0, lambda: self._set_busy(False))

    def _on_cancel(self):
        if self._downloader:
            self._downloader.cancel()
            self._log("⛔  Cancelling …")

    # ══════════════════════════════════════════════════════════════════════
    #  Helpers
    # ══════════════════════════════════════════════════════════════════════

    def _card(self, parent, expand=False) -> ctk.CTkFrame:
        """Create a styled card frame."""
        card = ctk.CTkFrame(
            parent, fg_color=CARD_BG,
            corner_radius=12, border_width=1, border_color=BORDER,
        )
        card.pack(fill="both", expand=expand, pady=(0, 10), padx=0)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=16, pady=12)
        return inner

    def _get_urls(self) -> list[str]:
        raw = self.url_textbox.get("1.0", "end").strip()
        urls: list[str] = []
        seen: set[str] = set()
        for url in (u.strip() for u in raw.splitlines()):
            if not url or url in seen:
                continue
            seen.add(url)
            urls.append(url)
        return urls

    def _set_busy(self, busy: bool, label: str = "Ready"):
        self._operation_active = busy
        if busy:
            self.download_btn.configure(state="disabled")
            self.fetch_btn.configure(state="disabled")
            self.cancel_btn.configure(state="normal")
            self.convert_btn.configure(state="disabled")
            self.progress_bar.set(0)
            self.progress_label.configure(text=label)
        else:
            self.download_btn.configure(state="normal")
            self.fetch_btn.configure(state="normal")
            self.cancel_btn.configure(state="disabled")
            self.convert_btn.configure(state="normal")
            self.progress_label.configure(text="Ready")
            self.speed_label.configure(text="")

    def _on_progress(self, percent: float, speed: str, eta: str):
        """Thread-safe progress update."""
        self.after(0, self._update_progress, percent, speed, eta)

    def _update_progress(self, percent: float, speed: str, eta: str):
        self.progress_bar.set(percent / 100)
        self.progress_label.configure(text=f"{percent:.1f}%")
        self.speed_label.configure(text=f"{speed}  •  ETA {eta}")

    def _log(self, message: str):
        """Thread-safe log append."""
        self.after(0, self._append_log, message)

    def _append_log(self, message: str):
        # Normalize trailing newlines so logs aren't double-spaced
        text = message.rstrip("\n")
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", text + "\n")
        # Ensure the scrollbar moves with new content if available
        try:
            self.log_textbox.see("end")
        except Exception:
            pass
        self.log_textbox.configure(state="disabled")


def launch():
    """Entry point – creates and runs the application."""
    app = App()
    app.mainloop()


if __name__ == "__main__":
    launch()
