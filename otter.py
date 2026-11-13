#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Otter — High-Performance Media Downloader powered by yt-dlp and PyQt6.
Theme: Pure Monochrome Line-Art (Linear / Vercel / Nothing OS style)
Palette: #09090B, #121215, #18181B, #27272A, #3F3F46, #71717A, #FAFAFA
Full yt-dlp feature integration: Audio/Video/Containers, Codecs, Subtitles,
SponsorBlock, Chapters, Browser Cookies, Multi-connection Turbo, and FFmpeg AAC fix.
"""

import os
import sys
import re
import json
import shutil
import ctypes
import subprocess
from pathlib import Path
from urllib.request import urlopen

from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QSize, QTimer, QRectF
)
from PyQt6.QtGui import (
    QIcon, QPixmap, QDesktopServices, QImage, QPainter, QColor, QPen, QPainterPath
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QProgressBar, QTextEdit,
    QFileDialog, QFrame, QButtonGroup, QMessageBox, QCheckBox, QScrollArea,
    QMenu
)

# ---------------------------------------------------------------------------
# Paths and Defaults
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
    BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))
else:
    APP_DIR = Path(__file__).resolve().parent
    BUNDLE_DIR = APP_DIR

YT_DLP_EXE = APP_DIR / "yt-dlp.exe"
CONFIG_FILE = APP_DIR / "otter_config.json"

ICON_SVG_MAIN = BUNDLE_DIR / "otter_icon_main.svg"
ICON_PNG_MAIN = BUNDLE_DIR / "otter_icon_main.png"
ICON_SVG_DESKTOP = BUNDLE_DIR / "otter_icon_desktop.svg"
ICON_PNG_DESKTOP = BUNDLE_DIR / "otter_icon_desktop.png"
ICON_ICO_DESKTOP = BUNDLE_DIR / "otter_icon_desktop.ico"
COOKIES_FILE = APP_DIR / "cookies.txt"

# Windows Silent Subprocess Configuration (Completely suppresses CMD window flashes)
SILENT_SUBPROCESS_KWARGS = {}
if os.name == 'nt':
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 0
    SILENT_SUBPROCESS_KWARGS = {
        "startupinfo": si,
        "creationflags": subprocess.CREATE_NO_WINDOW
    }

DEFAULT_DOWNLOAD_DIR = Path.home() / "Downloads"

DEFAULT_CONFIG = {
    "download_dir": str(DEFAULT_DOWNLOAD_DIR),
    "mode": "video",          # video, audio, video_only, playlist
    "quality_idx": 0,         # 0=Best, 1=1440p, 2=1080p, 3=720p, 4=480p, 5=360p
    "container_idx": 0,       # 0=MP4, 1=MKV, 2=WebM, 3=MOV
    "codec_idx": 0,           # 0=Auto, 1=Prefer H.264, 2=Prefer AV1/VP9
    "audio_fmt_idx": 0,       # 0=MP3, 1=M4A, 2=FLAC, 3=WAV, 4=OPUS, 5=OGG
    "audio_qual_idx": 0,      # 0=320k, 1=256k, 2=192k, 3=128k
    "playlist_type_idx": 0,   # 0=Video (MP4), 1=Audio (MP3)
    "playlist_range": "",     # e.g. "1:10"
    "embed_metadata": True,
    "embed_thumbnail": True,
    "clean_tags": True,
    "turbo_fragments": True,   # 4 concurrent fragments
    "use_node_runtime": True,
    "embed_subs": False,
    "auto_subs": False,
    "sub_lang_idx": 0,        # 0=uk,en, 1=en, 2=uk, 3=all, 4=ru,en
    "sub_fmt_idx": 0,         # 0=srt, 1=vtt, 2=ass
    "embed_chapters": True,
    "split_chapters": False,
    "sponsorblock_idx": 0,    # 0=Off, 1=Remove Sponsors, 2=Mark as Chapters
    "browser_cookies_idx": 0, # 0=None, 1=Chrome, 2=Firefox, 3=Edge, 4=Brave, 5=Opera
    "custom_cookies_path": "",
    "speed_limit_idx": 0,     # 0=Unlimited, 1=10M, 2=5M, 3=2M, 4=1M
    "custom_args": ""
}

def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                cfg.update(saved)
        except Exception:
            pass
    return cfg

def save_config(cfg: dict):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving config: {e}")

# ---------------------------------------------------------------------------
# FFmpeg Detection
# ---------------------------------------------------------------------------
def find_ffmpeg_dir() -> Path | None:
    """Finds directory containing ffmpeg.exe."""
    candidates = [
        APP_DIR,
        APP_DIR / "ffmpeg",
        Path(r"C:\Users\shal3nost\Documents\MyTools\ff"),
        Path(r"C:\ffmpeg\bin"),
        Path(r"C:\ProgramData\chocolatey\bin"),
    ]
    for c in candidates:
        if (c / "ffmpeg.exe").exists():
            return c

    which_ff = shutil.which("ffmpeg")
    if which_ff:
        p = Path(which_ff).parent
        if (p / "ffmpeg.exe").exists():
            return p
    return None

# ---------------------------------------------------------------------------
# Monochrome Logo & Icon Generator
# ---------------------------------------------------------------------------
def create_monochrome_icons(app_dir: Path):
    """
    1) Header Logo: crisp white silhouette from otter_icon_main.png / otter_icon_main.svg.
    2) Window/Desktop Icon: stylish rounded squircle from otter_icon_desktop.ico / otter_icon_desktop.png.
    """
    header_pix = None
    window_icon = None

    # 1. Header Logo
    main_png = None
    for p in [ICON_PNG_MAIN, app_dir / "otter_icon_main.png", BUNDLE_DIR / "otter_icon_main.png"]:
        if p.exists():
            main_png = p
            break

    if main_png:
        pix = QPixmap(str(main_png))
        if not pix.isNull():
            header_pix = pix.scaled(
                32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )

    if not header_pix or header_pix.isNull():
        main_svg = None
        for p in [ICON_SVG_MAIN, app_dir / "otter_icon_main.svg", BUNDLE_DIR / "otter_icon_main.svg"]:
            if p.exists():
                main_svg = p
                break
        if main_svg:
            try:
                from PyQt6.QtSvg import QSvgRenderer
                r = QSvgRenderer(str(main_svg))
                if r.isValid():
                    qimg = QImage(512, 512, QImage.Format.Format_ARGB32)
                    qimg.fill(Qt.GlobalColor.transparent)
                    p = QPainter(qimg)
                    r.render(p)
                    p.end()
                    # Crop transparent borders
                    w, h = qimg.width(), qimg.height()
                    ptr = qimg.bits()
                    ptr.setsize(h * qimg.bytesPerLine())
                    buf = bytearray(ptr)
                    min_x, max_x = w, 0
                    min_y, max_y = h, 0
                    bpl = qimg.bytesPerLine()
                    for y in range(h):
                        row = y * bpl
                        for x in range(w):
                            idx = row + x * 4
                            if buf[idx + 3] > 10:
                                if x < min_x: min_x = x
                                if x > max_x: max_x = x
                                if y < min_y: min_y = y
                                if y > max_y: max_y = y
                    if min_x < max_x and min_y < max_y:
                        cropped = qimg.copy(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)
                    else:
                        cropped = qimg
                    header_pix = QPixmap.fromImage(cropped).scaled(
                        32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
                    )
            except Exception:
                pass

    if not header_pix or header_pix.isNull():
        header_pix = QPixmap(32, 32)
        header_pix.fill(Qt.GlobalColor.transparent)

    # 2. Window / Desktop Icon
    ico_path = None
    for p in [ICON_ICO_DESKTOP, app_dir / "otter_icon_desktop.ico", BUNDLE_DIR / "otter_icon_desktop.ico"]:
        if p.exists():
            ico_path = p
            break

    if ico_path:
        window_icon = QIcon(str(ico_path))
    else:
        png_path = None
        for p in [ICON_PNG_DESKTOP, app_dir / "otter_icon_desktop.png", BUNDLE_DIR / "otter_icon_desktop.png"]:
            if p.exists():
                png_path = p
                break
        if png_path:
            window_icon = QIcon(str(png_path))
        else:
            window_icon = QIcon(header_pix)

    return header_pix, window_icon

# ---------------------------------------------------------------------------
# Background Worker: yt-dlp Auto-Update & Auto-Download
# ---------------------------------------------------------------------------
class UpdateWorker(QThread):
    status_signal = pyqtSignal(str, bool)

    def run(self):
        if not YT_DLP_EXE.exists():
            self.status_signal.emit("Downloading yt-dlp...", False)
            try:
                import urllib.request
                url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
                urllib.request.urlretrieve(url, str(YT_DLP_EXE))
                self.status_signal.emit("yt-dlp installed", True)
            except Exception:
                self.status_signal.emit("yt-dlp missing", False)
                return

        try:
            p_ver = subprocess.run(
                [str(YT_DLP_EXE), "--version"],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                **SILENT_SUBPROCESS_KWARGS
            )
            curr_ver = p_ver.stdout.strip() or "latest"

            p = subprocess.run(
                [str(YT_DLP_EXE), "-U"],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                **SILENT_SUBPROCESS_KWARGS
            )
            out = p.stdout.strip()

            if "up to date" in out.lower():
                self.status_signal.emit(f"yt-dlp {curr_ver}", True)
            elif "updated" in out.lower():
                p_new = subprocess.run(
                    [str(YT_DLP_EXE), "--version"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace",
                    **SILENT_SUBPROCESS_KWARGS
                )
                new_ver = p_new.stdout.strip() or curr_ver
                self.status_signal.emit(f"yt-dlp {new_ver}", True)
            else:
                self.status_signal.emit(f"yt-dlp {curr_ver}", True)
        except Exception:
            self.status_signal.emit("yt-dlp offline", False)

# ---------------------------------------------------------------------------
# Background Worker: Video Metadata Info
# ---------------------------------------------------------------------------
class InfoWorker(QThread):
    info_ready = pyqtSignal(dict)
    info_error = pyqtSignal(str)

    def __init__(self, url: str, cookies_args: list = None):
        super().__init__()
        self.url = url.strip()
        self.cookies_args = cookies_args or []

    def run(self):
        if not self.url:
            return

        cmd = [
            str(YT_DLP_EXE),
            "--dump-single-json",
            "--no-playlist",
            "--skip-download"
        ]
        cmd.extend(self.cookies_args)
        cmd.append(self.url)

        try:
            p = subprocess.run(
                cmd, capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=30,
                **SILENT_SUBPROCESS_KWARGS
            )
            if p.returncode == 0 and p.stdout.strip():
                data = json.loads(p.stdout)
                res = {
                    "title": data.get("title", "Untitled"),
                    "uploader": data.get("uploader") or data.get("channel", "Unknown Channel"),
                    "duration": data.get("duration", 0),
                    "view_count": data.get("view_count", 0),
                    "upload_date": data.get("upload_date", ""),
                    "thumbnail": data.get("thumbnail", "")
                }
                self.info_ready.emit(res)
            else:
                err = p.stderr.strip().splitlines()
                err_msg = err[-1] if err else "Could not fetch metadata"
                self.info_error.emit(err_msg)
        except subprocess.TimeoutExpired:
            self.info_error.emit("Metadata request timed out")
        except Exception as e:
            self.info_error.emit(str(e))

# ---------------------------------------------------------------------------
# Background Worker: yt-dlp Download Execution
# ---------------------------------------------------------------------------
class DownloadWorker(QThread):
    progress_signal = pyqtSignal(float, str, str, str)  # composite_pct, total_size, speed, eta
    status_signal = pyqtSignal(str)
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)  # success, message

    def __init__(self, cmd: list, working_dir: Path):
        super().__init__()
        self.cmd = cmd
        self.working_dir = working_dir
        self.process = None
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True
        if self.process:
            try:
                self.process.terminate()
            except Exception:
                pass

    def run(self):
        self._is_cancelled = False
        self.working_dir.mkdir(parents=True, exist_ok=True)
        self.log_signal.emit(f"Execute: {' '.join(self.cmd)}\n" + "—" * 60)

        # Snapshot files in working directory to accurately detect downloaded outputs
        before_snapshot = {}
        try:
            for f in self.working_dir.rglob("*"):
                if f.is_file():
                    try:
                        before_snapshot[str(f.resolve()).lower()] = f.stat().st_mtime
                    except Exception:
                        pass
        except Exception:
            pass

        try:
            self.process = subprocess.Popen(
                self.cmd,
                cwd=str(self.working_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                **SILENT_SUBPROCESS_KWARGS
            )

            # Robust regexes for yt-dlp progress and destination output
            prog_re = re.compile(
                r'\[download\]\s+([0-9\.]+)%\s+of\s+~?\s*([0-9\.]+[A-Za-z]+)(?:.*?\bat\s+([0-9\.]+[A-Za-z]+/s))?(?:.*?\bETA\s+([0-9:]+))?'
            )
            dest_re = re.compile(
                r'\[(?:download|Merger|ExtractAudio|VideoConvertor|FixupM4a|FixupM4v|ffmpeg)\]\s+Destination:\s+["\']?([^"\']+)["\']?',
                re.IGNORECASE
            )
            merger_re = re.compile(
                r'\[(?:Merger|ffmpeg)\]\s+Merging formats into\s+["\']?([^"\']+)["\']?',
                re.IGNORECASE
            )
            already_re = re.compile(
                r'\[download\]\s+["\']?([^"\']+)["\']?\s+has already been downloaded',
                re.IGNORECASE
            )
            fixup_re = re.compile(
                r'\[(?:FixupM4a|FixupM4v|Fixup)\]\s+Correcting container in\s+["\']?([^"\']+)["\']?',
                re.IGNORECASE
            )

            def to_abs_path(p_str: str) -> str:
                p_clean = p_str.strip(' "\'\t\r\n')
                if not p_clean:
                    return ""
                p = Path(p_clean)
                if not p.is_absolute():
                    p = self.working_dir / p
                return str(p.resolve())

            last_dest = ""
            current_stream = 0
            is_multistream = False

            for raw_line in self.process.stdout:
                if self._is_cancelled:
                    break

                line = raw_line.strip()
                if not line:
                    continue

                self.log_signal.emit(line)

                # Check if multi-stream (video + audio)
                if "[info]" in line and "Downloading" in line and "format(s):" in line:
                    if "+" in line:
                        is_multistream = True

                m_merge = merger_re.search(line)
                if m_merge:
                    last_dest = to_abs_path(m_merge.group(1))
                    self.status_signal.emit("Merging video & audio streams with FFmpeg...")
                    self.progress_signal.emit(98.5, "", "", "")
                    continue

                m_fix = fixup_re.search(line)
                if m_fix:
                    last_dest = to_abs_path(m_fix.group(1))
                    self.status_signal.emit("Fixing container format...")
                    continue

                m_alr = already_re.search(line)
                if m_alr:
                    last_dest = to_abs_path(m_alr.group(1))
                    self.status_signal.emit("File already downloaded")
                    continue

                m_dest = dest_re.search(line)
                if m_dest:
                    cand = to_abs_path(m_dest.group(1))
                    cand_name = os.path.basename(cand).lower()
                    if not re.search(r'\.f\d+\.', cand_name) and not cand_name.endswith(('.part', '.ytdl', '.temp', '.tmp')):
                        last_dest = cand
                    elif not last_dest:
                        last_dest = cand
                    current_stream += 1

                m_prog = prog_re.search(line)
                if m_prog:
                    try:
                        pct = float(m_prog.group(1))
                        total_size = m_prog.group(2)
                        speed = m_prog.group(3) or "—"
                        eta = m_prog.group(4) or "—"

                        # Multi-stream normalized progress to prevent 0-100% resetting
                        if is_multistream:
                            if current_stream <= 1:
                                composite = min(89.0, pct * 0.89)
                                phase_name = "video track"
                            else:
                                composite = 89.0 + min(9.0, pct * 0.09)
                                phase_name = "audio track"
                            self.status_signal.emit(f"Downloading {phase_name} ({total_size})")
                            self.progress_signal.emit(composite, total_size, speed, eta)
                        else:
                            self.status_signal.emit(f"Downloading ({total_size})")
                            self.progress_signal.emit(pct, total_size, speed, eta)
                    except Exception:
                        pass
                elif "[ExtractAudio]" in line:
                    self.status_signal.emit("Extracting & converting audio with FFmpeg...")
                    self.progress_signal.emit(96.0, "", "", "")
                elif "[SponsorBlock]" in line:
                    self.status_signal.emit("Processing SponsorBlock segments...")
                    self.progress_signal.emit(97.0, "", "", "")
                elif "[SplitChapters]" in line:
                    self.status_signal.emit("Splitting video into chapters...")
                elif "[EmbedSubtitle]" in line:
                    self.status_signal.emit("Embedding subtitles...")
                elif "[EmbedThumbnail]" in line:
                    self.status_signal.emit("Embedding cover art...")

            self.process.wait()

            if self._is_cancelled:
                self.finished_signal.emit(False, "Download cancelled by user.")
            elif self.process.returncode == 0:
                final_target = ""

                # 1. Check if parsed last_dest exists and is a file
                if last_dest and os.path.exists(last_dest) and os.path.isfile(last_dest):
                    final_target = last_dest
                else:
                    # 2. Check for newly created or modified files in working_dir (ignoring temp files)
                    temp_suffixes = ('.part', '.ytdl', '.temp', '.tmp')
                    candidates = []
                    try:
                        for f in self.working_dir.rglob("*"):
                            if f.is_file() and not f.name.endswith(temp_suffixes):
                                if re.search(r'\.f\d+\.', f.name):
                                    continue
                                f_abs = str(f.resolve())
                                f_lower = f_abs.lower()
                                try:
                                    mtime = f.stat().st_mtime
                                    if f_lower not in before_snapshot or mtime > before_snapshot[f_lower]:
                                        candidates.append((f_abs, mtime))
                                except Exception:
                                    pass
                    except Exception:
                        pass

                    if candidates:
                        candidates.sort(key=lambda x: x[1], reverse=True)
                        final_target = candidates[0][0]

                # 3. If still not found, check if last_dest was a directory or check newest media file
                if not final_target:
                    if last_dest and os.path.exists(last_dest):
                        final_target = last_dest
                    else:
                        media_exts = {'.mp4', '.mkv', '.webm', '.mov', '.mp3', '.m4a', '.flac', '.wav', '.opus', '.ogg'}
                        try:
                            media_files = [
                                f for f in self.working_dir.rglob("*")
                                if f.is_file() and f.suffix.lower() in media_exts and not f.name.endswith(temp_suffixes)
                            ]
                            if media_files:
                                media_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                                final_target = str(media_files[0].resolve())
                        except Exception:
                            pass

                # 4. Final fallback to working_dir itself
                if not final_target or not os.path.exists(final_target):
                    final_target = str(self.working_dir.resolve())

                self.finished_signal.emit(True, final_target)
            else:
                self.finished_signal.emit(False, f"yt-dlp exited with error code {self.process.returncode}")

        except Exception as e:
            self.finished_signal.emit(False, str(e))

# ---------------------------------------------------------------------------
# Main GUI Window
# ---------------------------------------------------------------------------
class OtterWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Otter")
        self.cfg = load_config()
        self.ffmpeg_dir = find_ffmpeg_dir()

        self.header_pixmap, self.app_icon = create_monochrome_icons(APP_DIR)
        if not self.app_icon.isNull():
            self.setWindowIcon(self.app_icon)

        self.download_worker = None
        self.info_worker = None
        self.update_worker = None
        self.last_downloaded_target = ""

        # Window constraints & dark titlebar
        self.setMinimumSize(850, 580)
        self.resize(880, 670)
        self.enable_dark_titlebar()

        self.init_ui()
        self.apply_styles()
        self.restore_settings()

        # Check updates on startup
        QTimer.singleShot(600, self.start_auto_update)

    def enable_dark_titlebar(self):
        if os.name == 'nt':
            try:
                hwnd = int(self.winId())
                DWMWA_USE_IMMERSIVE_DARK_MODE = 20
                val = ctypes.c_int(1)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(val), ctypes.sizeof(val)
                )
            except Exception:
                pass

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(20, 14, 20, 14)
        root_layout.setSpacing(8)

        # -------------------------------------------------------------------
        # 1. HEADER (Compact frameless bar)
        # -------------------------------------------------------------------
        header_row = QHBoxLayout()
        header_row.setSpacing(10)
        header_row.addSpacing(6)  # Subtle indent to align with content

        # Solid white filled otter logo
        self.lbl_logo = QLabel()
        self.lbl_logo.setFixedSize(32, 32)
        self.lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if not self.header_pixmap.isNull():
            self.lbl_logo.setPixmap(self.header_pixmap)
        header_row.addWidget(self.lbl_logo)

        lbl_app_name = QLabel("Otter")
        lbl_app_name.setObjectName("appTitle")
        header_row.addWidget(lbl_app_name)

        self.lbl_version_badge = QLabel("yt-dlp checking...")
        self.lbl_version_badge.setObjectName("versionBadge")
        header_row.addWidget(self.lbl_version_badge)

        if self.ffmpeg_dir:
            lbl_ff = QLabel("FFmpeg OK")
            lbl_ff.setObjectName("ffmpegBadge")
            lbl_ff.setToolTip(f"FFmpeg location: {self.ffmpeg_dir}")
            header_row.addWidget(lbl_ff)

        header_row.addStretch()

        self.btn_update = QPushButton("Update")
        self.btn_update.setObjectName("btnGhost")
        self.btn_update.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_update.clicked.connect(self.start_auto_update)
        header_row.addWidget(self.btn_update)

        root_layout.addLayout(header_row)

        # -------------------------------------------------------------------
        # CONTENT BODY (Pure frameless layout, no scrollbars)
        # -------------------------------------------------------------------
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setObjectName("mainScroll")
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll_widget = QWidget()
        body_layout = QVBoxLayout(scroll_widget)
        body_layout.setContentsMargins(0, 2, 0, 2)
        body_layout.setSpacing(10)

        # -------------------------------------------------------------------
        # 2. URL INPUT BAR
        # -------------------------------------------------------------------
        url_row = QHBoxLayout()
        url_row.setSpacing(8)

        self.url_input = QLineEdit()
        self.url_input.setObjectName("urlInput")
        self.url_input.setPlaceholderText("Paste URL...")
        self.url_input.setFixedHeight(38)
        self.url_input.returnPressed.connect(self.start_download)
        url_row.addWidget(self.url_input, stretch=1)

        self.btn_paste = QPushButton("Paste")
        self.btn_paste.setObjectName("btnSecondary")
        self.btn_paste.setFixedHeight(38)
        self.btn_paste.setFixedWidth(72)
        self.btn_paste.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_paste.clicked.connect(self.paste_from_clipboard)
        url_row.addWidget(self.btn_paste)

        self.btn_info = QPushButton("Info")
        self.btn_info.setObjectName("btnSecondary")
        self.btn_info.setFixedHeight(38)
        self.btn_info.setFixedWidth(64)
        self.btn_info.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_info.clicked.connect(self.fetch_metadata)
        url_row.addWidget(self.btn_info)

        body_layout.addLayout(url_row)

        # -------------------------------------------------------------------
        # 3. METADATA PREVIEW CARD (Collapsible)
        # -------------------------------------------------------------------
        self.preview_card = QFrame()
        self.preview_card.setObjectName("previewCard")
        self.preview_card.setVisible(False)

        prev_layout = QHBoxLayout(self.preview_card)
        prev_layout.setContentsMargins(12, 10, 12, 10)
        prev_layout.setSpacing(12)

        self.prev_thumb = QLabel()
        self.prev_thumb.setObjectName("previewThumb")
        self.prev_thumb.setFixedSize(84, 48)
        self.prev_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        prev_layout.addWidget(self.prev_thumb)

        prev_text = QVBoxLayout()
        prev_text.setSpacing(3)
        self.lbl_prev_title = QLabel("Video Title")
        self.lbl_prev_title.setObjectName("previewTitle")
        self.lbl_prev_meta = QLabel("Uploader • Duration")
        self.lbl_prev_meta.setObjectName("previewMeta")
        prev_text.addWidget(self.lbl_prev_title)
        prev_text.addWidget(self.lbl_prev_meta)
        prev_layout.addLayout(prev_text, stretch=1)

        self.btn_prev_close = QPushButton("✕")
        self.btn_prev_close.setObjectName("btnGhost")
        self.btn_prev_close.setFixedSize(24, 24)
        self.btn_prev_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_prev_close.clicked.connect(lambda: self.preview_card.setVisible(False))
        prev_layout.addWidget(self.btn_prev_close)

        body_layout.addWidget(self.preview_card)

        # -------------------------------------------------------------------
        # 4. SEGMENTED MODE SELECTOR
        # -------------------------------------------------------------------
        segmented_frame = QFrame()
        segmented_frame.setObjectName("segmentedFrame")
        seg_layout = QHBoxLayout(segmented_frame)
        seg_layout.setContentsMargins(3, 3, 3, 3)
        seg_layout.setSpacing(0)

        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)

        modes = [
            ("Video", "video"),
            ("Audio", "audio"),
            ("Video Only", "video_only"),
            ("Playlist", "playlist")
        ]

        for title, code in modes:
            btn = QPushButton(title)
            btn.setObjectName("btnSegmented")
            btn.setCheckable(True)
            btn.setProperty("mode_code", code)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(32)
            self.mode_group.addButton(btn)
            seg_layout.addWidget(btn)
            if code == "video":
                self.btn_mode_video = btn

        self.btn_mode_video.setChecked(True)
        self.mode_group.buttonToggled.connect(self.on_mode_toggled)
        body_layout.addWidget(segmented_frame)

        # -------------------------------------------------------------------
        # 5. PRIMARY SETTINGS (Dynamic dropdowns based on mode)
        # -------------------------------------------------------------------
        self.primary_settings_card = QFrame()
        self.primary_settings_card.setObjectName("settingsCard")
        self.ps_layout = QHBoxLayout(self.primary_settings_card)
        self.ps_layout.setContentsMargins(12, 8, 12, 8)
        self.ps_layout.setSpacing(10)

        # Widget 1: Quality (Video)
        self.w_col_quality = QWidget()
        vbox_q = QVBoxLayout(self.w_col_quality)
        vbox_q.setContentsMargins(0, 0, 0, 0)
        vbox_q.setSpacing(4)
        lbl_q = QLabel("Quality")
        lbl_q.setObjectName("dropdownLabel")
        self.combo_quality = QComboBox()
        self.combo_quality.setObjectName("darkCombo")
        self.combo_quality.addItems([
            "Best Available (4K / 2160p)",
            "1440p (2K QHD)",
            "1080p (Full HD)",
            "720p (HD)",
            "480p (SD)",
            "360p"
        ])
        self.combo_quality.setFixedHeight(34)
        vbox_q.addWidget(lbl_q)
        vbox_q.addWidget(self.combo_quality)
        self.ps_layout.addWidget(self.w_col_quality, stretch=2)

        # Widget 2: Container Format (Video / Playlist)
        self.w_col_format = QWidget()
        vbox_f = QVBoxLayout(self.w_col_format)
        vbox_f.setContentsMargins(0, 0, 0, 0)
        vbox_f.setSpacing(4)
        lbl_f = QLabel("Format")
        lbl_f.setObjectName("dropdownLabel")
        self.combo_format = QComboBox()
        self.combo_format.setObjectName("darkCombo")
        self.combo_format.addItems(["MP4 (Universal AAC)", "MKV (All Codecs)", "WebM", "MOV"])
        self.combo_format.setFixedHeight(34)
        vbox_f.addWidget(lbl_f)
        vbox_f.addWidget(self.combo_format)
        self.ps_layout.addWidget(self.w_col_format, stretch=2)

        # Widget 3: Video Codec Preference
        self.w_col_codec = QWidget()
        vbox_c = QVBoxLayout(self.w_col_codec)
        vbox_c.setContentsMargins(0, 0, 0, 0)
        vbox_c.setSpacing(4)
        lbl_c = QLabel("Codec")
        lbl_c.setObjectName("dropdownLabel")
        self.combo_codec = QComboBox()
        self.combo_codec.setObjectName("darkCombo")
        self.combo_codec.addItems(["Auto (Best Quality)", "Prefer H.264 (Compatible)", "Prefer AV1 / VP9 (Efficient)"])
        self.combo_codec.setFixedHeight(34)
        vbox_c.addWidget(lbl_c)
        vbox_c.addWidget(self.combo_codec)
        self.ps_layout.addWidget(self.w_col_codec, stretch=2)

        # Widget 4: Audio Format (Audio Mode)
        self.w_col_audio_fmt = QWidget()
        vbox_af = QVBoxLayout(self.w_col_audio_fmt)
        vbox_af.setContentsMargins(0, 0, 0, 0)
        vbox_af.setSpacing(4)
        lbl_af = QLabel("Format")
        lbl_af.setObjectName("dropdownLabel")
        self.combo_audio_fmt = QComboBox()
        self.combo_audio_fmt.setObjectName("darkCombo")
        self.combo_audio_fmt.addItems(["MP3 (Universal)", "M4A / AAC", "FLAC (Lossless)", "WAV", "OPUS", "OGG Vorbis"])
        self.combo_audio_fmt.setFixedHeight(34)
        vbox_af.addWidget(lbl_af)
        vbox_af.addWidget(self.combo_audio_fmt)
        self.ps_layout.addWidget(self.w_col_audio_fmt, stretch=2)

        # Widget 5: Audio Quality/Bitrate
        self.w_col_audio_qual = QWidget()
        vbox_aq = QVBoxLayout(self.w_col_audio_qual)
        vbox_aq.setContentsMargins(0, 0, 0, 0)
        vbox_aq.setSpacing(4)
        lbl_aq = QLabel("Bitrate")
        lbl_aq.setObjectName("dropdownLabel")
        self.combo_audio_qual = QComboBox()
        self.combo_audio_qual.setObjectName("darkCombo")
        self.combo_audio_qual.addItems(["320 kbps (Best)", "256 kbps", "192 kbps", "128 kbps"])
        self.combo_audio_qual.setFixedHeight(34)
        vbox_aq.addWidget(lbl_aq)
        vbox_aq.addWidget(self.combo_audio_qual)
        self.ps_layout.addWidget(self.w_col_audio_qual, stretch=1)

        # Widget 6: Playlist Items Range
        self.w_col_playlist_range = QWidget()
        vbox_pr = QVBoxLayout(self.w_col_playlist_range)
        vbox_pr.setContentsMargins(0, 0, 0, 0)
        vbox_pr.setSpacing(4)
        lbl_pr = QLabel("Item Range")
        lbl_pr.setObjectName("dropdownLabel")
        self.inp_playlist_range = QLineEdit()
        self.inp_playlist_range.setObjectName("darkInput")
        self.inp_playlist_range.setPlaceholderText("e.g. 1:10")
        self.inp_playlist_range.setFixedHeight(34)
        vbox_pr.addWidget(lbl_pr)
        vbox_pr.addWidget(self.inp_playlist_range)
        self.ps_layout.addWidget(self.w_col_playlist_range, stretch=1)

        # Initially hide audio and playlist specific widgets
        self.w_col_audio_fmt.setVisible(False)
        self.w_col_audio_qual.setVisible(False)
        self.w_col_playlist_range.setVisible(False)

        body_layout.addWidget(self.primary_settings_card)

        # -------------------------------------------------------------------
        # 6. DESTINATION FOLDER
        # -------------------------------------------------------------------
        path_row = QHBoxLayout()
        path_row.setSpacing(8)

        self.folder_input = QLineEdit()
        self.folder_input.setObjectName("pathInput")
        self.folder_input.setText(str(DEFAULT_DOWNLOAD_DIR))
        self.folder_input.setFixedHeight(34)
        self.folder_input.setToolTip("Destination folder for downloaded files. Double-click to open in File Explorer.")
        self.folder_input.mouseDoubleClickEvent = lambda event: self.open_destination_folder()
        path_row.addWidget(self.folder_input, stretch=1)

        self.btn_browse = QPushButton("Browse")
        self.btn_browse.setObjectName("btnSecondary")
        self.btn_browse.setFixedHeight(34)
        self.btn_browse.setFixedWidth(84)
        self.btn_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_browse.setToolTip("Select destination folder")
        self.btn_browse.clicked.connect(self.browse_folder)
        path_row.addWidget(self.btn_browse)

        body_layout.addLayout(path_row)

        # -------------------------------------------------------------------
        # 7. QUICK ACTION CHIPS (Pill toggles)
        # -------------------------------------------------------------------
        chips_row = QHBoxLayout()
        chips_row.setSpacing(8)

        self.chip_metadata = QPushButton("✓ Embed Metadata")
        self.chip_metadata.setObjectName("btnChip")
        self.chip_metadata.setCheckable(True)
        self.chip_metadata.setChecked(True)
        self.chip_metadata.setFixedHeight(28)
        self.chip_metadata.toggled.connect(lambda c: self.chip_metadata.setText("✓ Embed Metadata" if c else "Embed Metadata"))
        chips_row.addWidget(self.chip_metadata)

        self.chip_thumbnail = QPushButton("✓ Embed Artwork")
        self.chip_thumbnail.setObjectName("btnChip")
        self.chip_thumbnail.setCheckable(True)
        self.chip_thumbnail.setChecked(True)
        self.chip_thumbnail.setFixedHeight(28)
        self.chip_thumbnail.toggled.connect(lambda c: self.chip_thumbnail.setText("✓ Embed Artwork" if c else "Embed Artwork"))
        chips_row.addWidget(self.chip_thumbnail)

        self.chip_clean_tags = QPushButton("✓ Clean Tags")
        self.chip_clean_tags.setObjectName("btnChip")
        self.chip_clean_tags.setCheckable(True)
        self.chip_clean_tags.setChecked(True)
        self.chip_clean_tags.setFixedHeight(28)
        self.chip_clean_tags.toggled.connect(lambda c: self.chip_clean_tags.setText("✓ Clean Tags" if c else "Clean Tags"))
        chips_row.addWidget(self.chip_clean_tags)

        self.chip_turbo = QPushButton("✓ Turbo (4x)")
        self.chip_turbo.setObjectName("btnChip")
        self.chip_turbo.setCheckable(True)
        self.chip_turbo.setChecked(True)
        self.chip_turbo.setFixedHeight(28)
        self.chip_turbo.setToolTip("Download DASH fragments in 4 concurrent parallel streams for maximum speed")
        self.chip_turbo.toggled.connect(lambda c: self.chip_turbo.setText("✓ Turbo (4x)" if c else "Turbo (4x)"))
        chips_row.addWidget(self.chip_turbo)

        self.chip_node_runtime = QPushButton("✓ Node.js")
        self.chip_node_runtime.setObjectName("btnChip")
        self.chip_node_runtime.setCheckable(True)
        self.chip_node_runtime.setChecked(True)
        self.chip_node_runtime.setFixedHeight(28)
        self.chip_node_runtime.setToolTip("Use Node.js JavaScript runtime for YouTube signature deciphering")
        self.chip_node_runtime.toggled.connect(lambda c: self.chip_node_runtime.setText("✓ Node.js" if c else "Node.js"))
        chips_row.addWidget(self.chip_node_runtime)

        chips_row.addStretch()
        body_layout.addLayout(chips_row)

        # -------------------------------------------------------------------
        # 8. ADVANCED OPTIONS ACCORDION (Subtitles, SponsorBlock, Cookies, Network)
        # -------------------------------------------------------------------
        self.btn_toggle_advanced = QPushButton("> Advanced Options")
        self.btn_toggle_advanced.setObjectName("btnAdvancedToggle")
        self.btn_toggle_advanced.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_advanced.clicked.connect(self.toggle_advanced_panel)
        body_layout.addWidget(self.btn_toggle_advanced, alignment=Qt.AlignmentFlag.AlignLeft)

        self.advanced_panel = QFrame()
        self.advanced_panel.setObjectName("advancedPanel")
        self.advanced_panel.setVisible(False)
        adv_grid = QGridLayout(self.advanced_panel)
        adv_grid.setContentsMargins(22, 12, 16, 12)
        adv_grid.setHorizontalSpacing(16)
        adv_grid.setVerticalSpacing(10)
        adv_grid.setColumnStretch(0, 0)
        adv_grid.setColumnStretch(1, 1)

        # Row 0: Subtitles
        self.chk_embed_subs = QCheckBox("Embed Subtitles")
        self.chk_embed_subs.setObjectName("darkCheck")
        self.chk_auto_subs = QCheckBox("Auto-generated")
        self.chk_auto_subs.setObjectName("darkCheck")

        self.combo_sub_lang = QComboBox()
        self.combo_sub_lang.setObjectName("darkCombo")
        self.combo_sub_lang.addItems([
            "uk, en (Ukrainian & English)",
            "en (English)",
            "uk (Ukrainian)",
            "all (All Languages)",
            "ru, en (Russian & English)"
        ])
        self.combo_sub_lang.setFixedHeight(30)

        self.combo_sub_fmt = QComboBox()
        self.combo_sub_fmt.setObjectName("darkCombo")
        self.combo_sub_fmt.addItems(["SRT (SubRip)", "VTT (WebVTT)", "ASS (Advanced)"])
        self.combo_sub_fmt.setFixedHeight(30)
        self.combo_sub_fmt.setFixedWidth(130)

        subs_box = QHBoxLayout()
        subs_box.setSpacing(10)
        subs_box.addWidget(self.chk_embed_subs)
        subs_box.addWidget(self.chk_auto_subs)
        subs_box.addWidget(self.combo_sub_lang, stretch=1)
        subs_box.addWidget(self.combo_sub_fmt)

        lbl_subs = QLabel("Subtitles")
        lbl_subs.setObjectName("dropdownLabel")
        lbl_subs.setFixedWidth(115)
        adv_grid.addWidget(lbl_subs, 0, 0)
        adv_grid.addLayout(subs_box, 0, 1)

        # Row 1: Chapters & SponsorBlock
        self.chk_embed_chapters = QCheckBox("Embed Chapters")
        self.chk_embed_chapters.setObjectName("darkCheck")
        self.chk_embed_chapters.setChecked(True)

        self.chk_split_chapters = QCheckBox("Split Chapters")
        self.chk_split_chapters.setObjectName("darkCheck")
        self.chk_split_chapters.setToolTip("Split video/album into individual files per chapter")

        self.combo_sponsorblock = QComboBox()
        self.combo_sponsorblock.setObjectName("darkCombo")
        self.combo_sponsorblock.addItems([
            "SponsorBlock: Off",
            "SponsorBlock: Auto-cut",
            "SponsorBlock: Mark Chapters"
        ])
        self.combo_sponsorblock.setFixedHeight(30)

        ch_box = QHBoxLayout()
        ch_box.setSpacing(10)
        ch_box.addWidget(self.chk_embed_chapters)
        ch_box.addWidget(self.chk_split_chapters)
        ch_box.addWidget(self.combo_sponsorblock, stretch=1)

        lbl_chap = QLabel("Chapters")
        lbl_chap.setObjectName("dropdownLabel")
        lbl_chap.setFixedWidth(115)
        adv_grid.addWidget(lbl_chap, 1, 0)
        adv_grid.addLayout(ch_box, 1, 1)

        # Row 2: Browser Cookies & Auth
        self.combo_browser_cookies = QComboBox()
        self.combo_browser_cookies.setObjectName("darkCombo")
        self.combo_browser_cookies.addItems([
            "Browser: None",
            "Browser: Brave",
            "Browser: Chrome",
            "Browser: Firefox",
            "Browser: Edge",
            "Browser: Opera",
            "Browser: Vivaldi"
        ])
        self.combo_browser_cookies.setFixedHeight(30)
        self.combo_browser_cookies.setFixedWidth(180)
        self.combo_browser_cookies.setToolTip("Extract cookies from local browser to bypass age restrictions and login gates")

        self.inp_cookies_file = QLineEdit()
        self.inp_cookies_file.setObjectName("darkInput")
        self.inp_cookies_file.setPlaceholderText("Cookies file...")
        self.inp_cookies_file.setFixedHeight(30)

        self.btn_pick_cookies = QPushButton("...")
        self.btn_pick_cookies.setObjectName("btnSecondary")
        self.btn_pick_cookies.setFixedSize(30, 30)
        self.btn_pick_cookies.clicked.connect(self.browse_cookies_file)

        ck_box = QHBoxLayout()
        ck_box.setSpacing(8)
        ck_box.addWidget(self.combo_browser_cookies)
        ck_box.addWidget(self.inp_cookies_file, stretch=1)
        ck_box.addWidget(self.btn_pick_cookies)

        lbl_auth = QLabel("Authentication")
        lbl_auth.setObjectName("dropdownLabel")
        lbl_auth.setFixedWidth(115)
        adv_grid.addWidget(lbl_auth, 2, 0)
        adv_grid.addLayout(ck_box, 2, 1)

        # Row 3: Speed & Limits
        self.combo_speed_limit = QComboBox()
        self.combo_speed_limit.setObjectName("darkCombo")
        self.combo_speed_limit.addItems([
            "Speed: Unlimited",
            "Speed: 10 MB/s",
            "Speed: 5 MB/s",
            "Speed: 2 MB/s",
            "Speed: 1 MB/s"
        ])
        self.combo_speed_limit.setFixedHeight(30)
        self.combo_speed_limit.setFixedWidth(180)

        self.inp_custom_args = QLineEdit()
        self.inp_custom_args.setObjectName("darkInput")
        self.inp_custom_args.setPlaceholderText("Custom arguments (e.g. --geo-bypass)")
        self.inp_custom_args.setFixedHeight(30)

        net_box = QHBoxLayout()
        net_box.setSpacing(8)
        net_box.addWidget(self.combo_speed_limit)
        net_box.addWidget(self.inp_custom_args, stretch=1)

        lbl_net = QLabel("Network & Args")
        lbl_net.setObjectName("dropdownLabel")
        lbl_net.setFixedWidth(115)
        adv_grid.addWidget(lbl_net, 3, 0)
        adv_grid.addLayout(net_box, 3, 1)

        body_layout.addWidget(self.advanced_panel)
        body_layout.addStretch()

        self.scroll_area.setWidget(scroll_widget)
        root_layout.addWidget(self.scroll_area, stretch=1)

        # -------------------------------------------------------------------
        # 9. FIXED BOTTOM CONTROLS: Progress, Buttons, Logs Console
        # -------------------------------------------------------------------
        bottom_container = QWidget()
        bottom_layout = QVBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(0, 4, 0, 0)
        bottom_layout.setSpacing(8)

        # Status & Percentage header
        status_header_row = QHBoxLayout()
        self.lbl_status = QLabel("Ready")
        self.lbl_status.setObjectName("statusText")

        self.lbl_metrics = QLabel("")
        self.lbl_metrics.setObjectName("metricsText")

        self.lbl_percent = QLabel("0%")
        self.lbl_percent.setObjectName("percentText")

        status_header_row.addWidget(self.lbl_status)
        status_header_row.addWidget(self.lbl_metrics)
        status_header_row.addStretch()
        status_header_row.addWidget(self.lbl_percent)
        bottom_layout.addLayout(status_header_row)

        # Ultra-thin 4px monochrome progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("monochromeBar")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #18181B;
                border: none;
                border-radius: 2px;
                height: 4px;
            }
            QProgressBar::chunk {
                background-color: #FAFAFA;
                border-radius: 2px;
            }
        """)
        bottom_layout.addWidget(self.progress_bar)

        # Action Buttons
        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        self.btn_download = QPushButton("Download")
        self.btn_download.setObjectName("btnPrimary")
        self.btn_download.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_download.setFixedHeight(40)
        self.btn_download.clicked.connect(self.start_download)
        action_row.addWidget(self.btn_download, stretch=1)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("btnSecondary")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setFixedHeight(40)
        self.btn_cancel.setFixedWidth(90)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_download)
        action_row.addWidget(self.btn_cancel)

        self.btn_open_file = QPushButton("Open File")
        self.btn_open_file.setObjectName("btnSecondary")
        self.btn_open_file.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_file.setFixedHeight(40)
        self.btn_open_file.setFixedWidth(100)
        self.btn_open_file.setEnabled(False)
        self.btn_open_file.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.btn_open_file.customContextMenuRequested.connect(self.show_open_file_menu)
        self.btn_open_file.clicked.connect(self.open_last_downloaded)
        action_row.addWidget(self.btn_open_file)

        self.btn_logs_toggle = QPushButton("> Logs")
        self.btn_logs_toggle.setObjectName("btnLogsToggle")
        self.btn_logs_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_logs_toggle.setFixedHeight(40)
        self.btn_logs_toggle.setFixedWidth(75)
        self.btn_logs_toggle.clicked.connect(self.toggle_log_console)
        action_row.addWidget(self.btn_logs_toggle)

        bottom_layout.addLayout(action_row)

        # Log Console (Dynamic resize)
        self.log_console = QTextEdit()
        self.log_console.setObjectName("logConsole")
        self.log_console.setReadOnly(True)
        self.log_console.setFixedHeight(120)
        self.log_console.setVisible(False)
        bottom_layout.addWidget(self.log_console)

        root_layout.addWidget(bottom_container)

    # -----------------------------------------------------------------------
    # Dynamic Mode View Handling
    # -----------------------------------------------------------------------
    def on_mode_toggled(self, button, checked):
        if not checked:
            return
        mode = button.property("mode_code")

        if mode == "video":
            self.w_col_quality.setVisible(True)
            self.w_col_format.setVisible(True)
            self.w_col_codec.setVisible(True)
            self.w_col_audio_fmt.setVisible(False)
            self.w_col_audio_qual.setVisible(False)
            self.w_col_playlist_range.setVisible(False)
            self.combo_format.clear()
            self.combo_format.addItems(["MP4 (Universal AAC)", "MKV (All Codecs)", "WebM", "MOV"])
        elif mode == "audio":
            self.w_col_quality.setVisible(False)
            self.w_col_format.setVisible(False)
            self.w_col_codec.setVisible(False)
            self.w_col_audio_fmt.setVisible(True)
            self.w_col_audio_qual.setVisible(True)
            self.w_col_playlist_range.setVisible(False)
        elif mode == "video_only":
            self.w_col_quality.setVisible(True)
            self.w_col_format.setVisible(True)
            self.w_col_codec.setVisible(False)
            self.w_col_audio_fmt.setVisible(False)
            self.w_col_audio_qual.setVisible(False)
            self.w_col_playlist_range.setVisible(False)
            self.combo_format.clear()
            self.combo_format.addItems(["MP4", "MKV", "WebM"])
        elif mode == "playlist":
            self.w_col_quality.setVisible(True)
            self.w_col_format.setVisible(True)
            self.w_col_codec.setVisible(False)
            self.w_col_audio_fmt.setVisible(False)
            self.w_col_audio_qual.setVisible(False)
            self.w_col_playlist_range.setVisible(True)
            self.combo_format.clear()
            self.combo_format.addItems(["MP4 Video", "MP3 Audio", "MKV Video", "FLAC Audio"])

    # -----------------------------------------------------------------------
    # Dynamic Window Resizing for Logs & Advanced Panels
    # -----------------------------------------------------------------------
    def toggle_log_console(self):
        is_vis = not self.log_console.isVisible()
        self.log_console.setVisible(is_vis)
        self.btn_logs_toggle.setText("v Logs" if is_vis else "> Logs")
        if is_vis:
            self.resize(self.width(), self.height() + 130)
        else:
            self.resize(self.width(), max(self.minimumHeight(), self.height() - 130))
        self.updateGeometry()

    def toggle_advanced_panel(self):
        is_vis = not self.advanced_panel.isVisible()
        self.advanced_panel.setVisible(is_vis)
        self.btn_toggle_advanced.setText("v Advanced Options" if is_vis else "> Advanced Options")
        self.updateGeometry()

    # -----------------------------------------------------------------------
    # QSS Styling (Pure Monochrome Line-Art Theme)
    # -----------------------------------------------------------------------
    def apply_styles(self):
        qss = """
        QMainWindow {
            background-color: #09090B;
        }
        QWidget {
            background-color: #09090B;
            color: #FAFAFA;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            font-size: 13px;
        }
        #mainScroll {
            background: transparent;
            border: none;
        }
        #mainScroll QScrollBar:vertical {
            background: #09090B;
            width: 8px;
            margin: 0px;
        }
        #mainScroll QScrollBar::handle:vertical {
            background: #27272A;
            min-height: 24px;
            border-radius: 4px;
        }
        #mainScroll QScrollBar::handle:vertical:hover {
            background: #3F3F46;
        }
        #mainScroll QScrollBar::add-line:vertical, #mainScroll QScrollBar::sub-line:vertical {
            height: 0px;
        }

        /* Header */
        #appTitle {
            font-size: 20px;
            font-weight: 700;
            color: #FAFAFA;
            letter-spacing: -0.5px;
        }
        #versionBadge {
            font-size: 11px;
            color: #71717A;
            background-color: #18181B;
            border: 1px solid #27272A;
            border-radius: 4px;
            padding: 2px 8px;
            font-weight: 500;
        }
        #ffmpegBadge {
            font-size: 10px;
            color: #A1A1AA;
            background-color: #18181B;
            border: 1px solid #27272A;
            border-radius: 4px;
            padding: 2px 6px;
            font-weight: 600;
        }
        #btnGhost {
            background-color: transparent;
            color: #71717A;
            border: none;
            padding: 4px 8px;
            font-size: 12px;
            border-radius: 4px;
        }
        #btnGhost:hover {
            color: #FAFAFA;
            background-color: #18181B;
        }

        /* Inputs */
        #urlInput, #pathInput, #darkInput {
            background-color: #121215;
            border: 1px solid #27272A;
            border-radius: 6px;
            padding: 6px 12px;
            color: #FAFAFA;
            selection-background-color: #27272A;
            selection-color: #FAFAFA;
        }
        #urlInput:focus, #pathInput:focus, #darkInput:focus {
            border: 1px solid #71717A;
            background-color: #18181B;
        }

        /* Secondary Button */
        #btnSecondary {
            background-color: #18181B;
            color: #FAFAFA;
            border: 1px solid #27272A;
            border-radius: 6px;
            font-weight: 500;
            padding: 0 12px;
        }
        #btnSecondary:hover {
            background-color: #27272A;
            border: 1px solid #3F3F46;
        }
        #btnSecondary:pressed {
            background-color: #121215;
        }
        #btnSecondary:disabled {
            color: #3F3F46;
            border: 1px solid #18181B;
            background-color: #121215;
        }

        /* Primary Button */
        #btnPrimary {
            background-color: #FAFAFA;
            color: #09090B;
            border: 1px solid #FAFAFA;
            border-radius: 6px;
            font-weight: 600;
            font-size: 14px;
            padding: 0 20px;
        }
        #btnPrimary:hover {
            background-color: #E4E4E7;
            border: 1px solid #E4E4E7;
        }
        #btnPrimary:pressed {
            background-color: #D4D4D8;
        }
        #btnPrimary:disabled {
            background-color: #18181B;
            color: #52525B;
            border: 1px solid #27272A;
        }

        /* Segmented Frame */
        #segmentedFrame {
            background-color: #121215;
            border: 1px solid #27272A;
            border-radius: 6px;
            min-height: 34px;
        }
        #btnSegmented {
            background-color: transparent;
            color: #71717A;
            border: none;
            border-radius: 4px;
            font-weight: 500;
            padding: 4px 14px;
            font-size: 12px;
        }
        #btnSegmented:hover {
            color: #FAFAFA;
        }
        #btnSegmented:checked {
            background-color: #FAFAFA;
            color: #09090B;
            font-weight: 600;
        }

        /* Cards */
        #settingsCard, #previewCard, #advancedPanel {
            background-color: #121215;
            border: 1px solid #27272A;
            border-radius: 6px;
        }
        #dropdownLabel {
            background: transparent;
            background-color: transparent;
            border: none;
            font-size: 11px;
            font-weight: 500;
            color: #71717A;
        }

        /* Dropdowns */
        #darkCombo {
            background-color: #18181B;
            color: #FAFAFA;
            border: 1px solid #27272A;
            border-radius: 6px;
            padding: 4px 10px;
        }
        #darkCombo:hover {
            border: 1px solid #3F3F46;
        }
        #darkCombo::drop-down {
            border: none;
            width: 20px;
        }
        #darkCombo QAbstractItemView {
            background-color: #121215;
            color: #FAFAFA;
            selection-background-color: #27272A;
            selection-color: #FAFAFA;
            border: 1px solid #27272A;
            padding: 4px;
            outline: none;
        }

        /* Chips */
        #btnChip {
            background-color: #121215;
            color: #71717A;
            border: 1px solid #27272A;
            border-radius: 14px;
            padding: 0 12px;
            font-size: 11px;
            font-weight: 500;
        }
        #btnChip:hover {
            color: #A1A1AA;
            border: 1px solid #3F3F46;
        }
        #btnChip:checked {
            background-color: #18181B;
            color: #FAFAFA;
            border: 1px solid #52525B;
        }

        /* Advanced Options Toggle */
        #btnAdvancedToggle, #btnLogsToggle {
            background-color: transparent;
            color: #71717A;
            border: none;
            font-size: 12px;
            font-weight: 500;
            padding: 4px 6px;
            border-radius: 4px;
        }
        #btnAdvancedToggle:hover, #btnLogsToggle:hover {
            color: #FAFAFA;
            background-color: #18181B;
        }

        /* Checkbox */
        #darkCheck {
            color: #FAFAFA;
            font-size: 12px;
        }
        #darkCheck::indicator {
            width: 16px;
            height: 16px;
            border: 1px solid #27272A;
            border-radius: 4px;
            background-color: #18181B;
        }
        #darkCheck::indicator:hover {
            border: 1px solid #52525B;
        }
        #darkCheck::indicator:checked {
            background-color: #FAFAFA;
            border: 1px solid #FAFAFA;
            image: none;
        }

        /* Status & Progress */
        #statusText {
            color: #FAFAFA;
            font-weight: 500;
            font-size: 13px;
        }
        #metricsText {
            color: #71717A;
            font-size: 12px;
            margin-left: 8px;
        }
        #percentText {
            color: #FAFAFA;
            font-weight: 600;
            font-size: 13px;
        }
        QProgressBar {
            background-color: #18181B;
            border: none;
            border-radius: 2px;
            height: 4px;
            text-align: center;
        }
        QProgressBar::chunk {
            background-color: #FAFAFA;
            border-radius: 2px;
        }

        /* Log Console */
        #logConsole {
            background-color: #000000;
            color: #A1A1AA;
            border: 1px solid #27272A;
            border-radius: 6px;
            padding: 8px;
            font-family: "Cascadia Code", Consolas, "Courier New", monospace;
            font-size: 11px;
            line-height: 1.4;
        }

        /* Scrollbars (completely hidden) */
        QScrollBar:vertical, QScrollBar:horizontal {
            width: 0px;
            height: 0px;
            background: transparent;
            border: none;
        }
        """
        self.setStyleSheet(qss)

    # -----------------------------------------------------------------------
    # UI Actions & Helpers
    # -----------------------------------------------------------------------
    def paste_from_clipboard(self):
        cb = QApplication.clipboard()
        text = cb.text().strip()
        if text:
            self.url_input.setText(text)
            self.fetch_metadata()

    def browse_folder(self):
        curr = self.folder_input.text().strip() or str(DEFAULT_DOWNLOAD_DIR)
        path = QFileDialog.getExistingDirectory(self, "Select Download Directory", curr)
        if path:
            self.folder_input.setText(path)
            self.save_current_settings()

    def open_destination_folder(self):
        curr = self.folder_input.text().strip() or str(DEFAULT_DOWNLOAD_DIR)
        p = Path(curr)
        p.mkdir(parents=True, exist_ok=True)
        if os.name == 'nt':
            os.startfile(str(p))

    def browse_cookies_file(self):
        f, _ = QFileDialog.getOpenTextFile(self, "Select cookies.txt File", "", "Text Files (*.txt);;All Files (*.*)")
        if f:
            self.inp_cookies_file.setText(f)

    def open_last_downloaded(self):
        target = self.last_downloaded_target
        if not target or not os.path.exists(target):
            target = self.folder_input.text().strip() or str(DEFAULT_DOWNLOAD_DIR)

        if not target or not os.path.exists(target):
            QMessageBox.warning(self, "Target Missing", "Downloaded file or target directory does not exist.")
            return

        target_norm = os.path.normpath(target)
        try:
            os.startfile(target_norm)
        except Exception:
            try:
                if os.path.isfile(target_norm):
                    subprocess.run(["explorer.exe", f"/select,{target_norm}"], **SILENT_SUBPROCESS_KWARGS)
                else:
                    subprocess.run(["explorer.exe", target_norm], **SILENT_SUBPROCESS_KWARGS)
            except Exception as e:
                QMessageBox.warning(self, "Error Opening", f"Could not open target:\n{e}")

    def reveal_last_downloaded(self):
        target = self.last_downloaded_target
        if not target or not os.path.exists(target):
            target = self.folder_input.text().strip() or str(DEFAULT_DOWNLOAD_DIR)

        if not target or not os.path.exists(target):
            return

        target_norm = os.path.normpath(target)
        try:
            if os.path.isfile(target_norm):
                subprocess.run(["explorer.exe", f"/select,{target_norm}"], **SILENT_SUBPROCESS_KWARGS)
            else:
                os.startfile(target_norm)
        except Exception:
            pass

    def show_open_file_menu(self, pos):
        if not self.btn_open_file.isEnabled() or not self.last_downloaded_target:
            return

        target = os.path.normpath(self.last_downloaded_target)
        if not os.path.exists(target):
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #121215;
                color: #FAFAFA;
                border: 1px solid #27272A;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 18px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #27272A;
                color: #FAFAFA;
            }
        """)

        if os.path.isfile(target):
            act_open = menu.addAction("Open / Play File")
            act_reveal = menu.addAction("Show in File Explorer")
            act_folder = menu.addAction("Open Download Directory")
        else:
            act_open = menu.addAction("Open Folder")
            act_reveal = None
            act_folder = None

        chosen = menu.exec(self.btn_open_file.mapToGlobal(pos))
        if chosen == act_open:
            self.open_last_downloaded()
        elif act_reveal and chosen == act_reveal:
            self.reveal_last_downloaded()
        elif act_folder and chosen == act_folder:
            self.open_destination_folder()

    def start_auto_update(self):
        self.btn_update.setEnabled(False)
        self.lbl_version_badge.setText("updating...")
        self.update_worker = UpdateWorker()
        self.update_worker.status_signal.connect(self.on_update_result)
        self.update_worker.start()

    def on_update_result(self, text: str, is_success: bool):
        self.lbl_version_badge.setText(text)
        self.btn_update.setEnabled(True)

    def fetch_metadata(self):
        url = self.url_input.text().strip()
        if not url:
            return

        self.btn_info.setEnabled(False)
        self.lbl_status.setText("Fetching metadata...")

        # Cookies for metadata if configured
        cookies_args = []
        b_idx = self.combo_browser_cookies.currentIndex()
        browser_map = {1: "brave", 2: "chrome", 3: "firefox", 4: "edge", 5: "opera", 6: "vivaldi"}
        if b_idx in browser_map:
            cookies_args.extend(["--cookies-from-browser", browser_map[b_idx]])
        c_file = self.inp_cookies_file.text().strip()
        if c_file and os.path.exists(c_file):
            cookies_args.extend(["--cookies", c_file])

        self.info_worker = InfoWorker(url, cookies_args)
        self.info_worker.info_ready.connect(self.on_info_ready)
        self.info_worker.info_error.connect(self.on_info_error)
        self.info_worker.start()

    def on_info_ready(self, info: dict):
        self.btn_info.setEnabled(True)
        self.lbl_status.setText("Ready")

        title = info.get("title", "")
        uploader = info.get("uploader", "")
        dur = info.get("duration", 0)
        views = info.get("view_count", 0)

        mins = dur // 60
        secs = dur % 60
        dur_str = f"{mins}:{secs:02d}" if dur > 0 else "Live / Unknown"
        views_str = f" • {views:,} views" if views > 0 else ""

        self.lbl_prev_title.setText(title)
        self.lbl_prev_meta.setText(f"{uploader} • {dur_str}{views_str}")
        self.preview_card.setVisible(True)

        thumb_url = info.get("thumbnail")
        if thumb_url:
            QTimer.singleShot(10, lambda: self.load_thumbnail(thumb_url))

    def on_info_error(self, err: str):
        self.btn_info.setEnabled(True)
        self.lbl_status.setText(f"Info Error: {err[:60]}")

    def load_thumbnail(self, url: str):
        try:
            with urlopen(url, timeout=5) as resp:
                data = resp.read()
                img = QImage.fromData(data)
                if not img.isNull():
                    scaled = img.scaled(
                        84, 48, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.prev_thumb.setPixmap(QPixmap.fromImage(scaled))
        except Exception:
            pass

    # -----------------------------------------------------------------------
    # Settings Restoration & Persistence
    # -----------------------------------------------------------------------
    def restore_settings(self):
        c = self.cfg
        self.folder_input.setText(c.get("download_dir", str(DEFAULT_DOWNLOAD_DIR)))

        mode = c.get("mode", "video")
        for btn in self.mode_group.buttons():
            if btn.property("mode_code") == mode:
                btn.setChecked(True)
                break

        self.combo_quality.setCurrentIndex(min(c.get("quality_idx", 0), self.combo_quality.count() - 1))
        self.combo_format.setCurrentIndex(min(c.get("container_idx", 0), self.combo_format.count() - 1))
        self.combo_codec.setCurrentIndex(min(c.get("codec_idx", 0), self.combo_codec.count() - 1))
        self.combo_audio_fmt.setCurrentIndex(min(c.get("audio_fmt_idx", 0), self.combo_audio_fmt.count() - 1))
        self.combo_audio_qual.setCurrentIndex(min(c.get("audio_qual_idx", 0), self.combo_audio_qual.count() - 1))
        self.inp_playlist_range.setText(c.get("playlist_range", ""))

        self.chip_metadata.setChecked(c.get("embed_metadata", True))
        self.chip_thumbnail.setChecked(c.get("embed_thumbnail", True))
        self.chip_clean_tags.setChecked(c.get("clean_tags", True))
        self.chip_turbo.setChecked(c.get("turbo_fragments", True))
        self.chip_node_runtime.setChecked(c.get("use_node_runtime", True))

        self.chk_embed_subs.setChecked(c.get("embed_subs", False))
        self.chk_auto_subs.setChecked(c.get("auto_subs", False))
        self.combo_sub_lang.setCurrentIndex(min(c.get("sub_lang_idx", 0), self.combo_sub_lang.count() - 1))
        self.combo_sub_fmt.setCurrentIndex(min(c.get("sub_fmt_idx", 0), self.combo_sub_fmt.count() - 1))

        self.chk_embed_chapters.setChecked(c.get("embed_chapters", True))
        self.chk_split_chapters.setChecked(c.get("split_chapters", False))
        self.combo_sponsorblock.setCurrentIndex(min(c.get("sponsorblock_idx", 0), self.combo_sponsorblock.count() - 1))

        self.combo_browser_cookies.setCurrentIndex(min(c.get("browser_cookies_idx", 0), self.combo_browser_cookies.count() - 1))
        self.inp_cookies_file.setText(c.get("custom_cookies_path", ""))
        self.combo_speed_limit.setCurrentIndex(min(c.get("speed_limit_idx", 0), self.combo_speed_limit.count() - 1))
        self.inp_custom_args.setText(c.get("custom_args", ""))

    def save_current_settings(self):
        checked_btn = self.mode_group.checkedButton()
        mode = checked_btn.property("mode_code") if checked_btn else "video"

        c = {
            "download_dir": self.folder_input.text().strip(),
            "mode": mode,
            "quality_idx": self.combo_quality.currentIndex(),
            "container_idx": self.combo_format.currentIndex(),
            "codec_idx": self.combo_codec.currentIndex(),
            "audio_fmt_idx": self.combo_audio_fmt.currentIndex(),
            "audio_qual_idx": self.combo_audio_qual.currentIndex(),
            "playlist_range": self.inp_playlist_range.text().strip(),
            "embed_metadata": self.chip_metadata.isChecked(),
            "embed_thumbnail": self.chip_thumbnail.isChecked(),
            "clean_tags": self.chip_clean_tags.isChecked(),
            "turbo_fragments": self.chip_turbo.isChecked(),
            "use_node_runtime": self.chip_node_runtime.isChecked(),
            "embed_subs": self.chk_embed_subs.isChecked(),
            "auto_subs": self.chk_auto_subs.isChecked(),
            "sub_lang_idx": self.combo_sub_lang.currentIndex(),
            "sub_fmt_idx": self.combo_sub_fmt.currentIndex(),
            "embed_chapters": self.chk_embed_chapters.isChecked(),
            "split_chapters": self.chk_split_chapters.isChecked(),
            "sponsorblock_idx": self.combo_sponsorblock.currentIndex(),
            "browser_cookies_idx": self.combo_browser_cookies.currentIndex(),
            "custom_cookies_path": self.inp_cookies_file.text().strip(),
            "speed_limit_idx": self.combo_speed_limit.currentIndex(),
            "custom_args": self.inp_custom_args.text().strip()
        }
        self.cfg.update(c)
        save_config(self.cfg)

    # -----------------------------------------------------------------------
    # Command Construction & Download Execution
    # -----------------------------------------------------------------------
    def build_command(self, url: str) -> list:
        cmd = [str(YT_DLP_EXE), "--newline"]

        # 1. FFmpeg Location (Guarantees yt-dlp always finds FFmpeg)
        if self.ffmpeg_dir:
            cmd.extend(["--ffmpeg-location", str(self.ffmpeg_dir)])

        # 2. Concurrency / Turbo Fragments
        if self.chip_turbo.isChecked():
            cmd.extend(["-N", "4"])

        # 3. Node.js JavaScript Engine
        if self.chip_node_runtime.isChecked():
            cmd.extend(["--js-runtimes", "node"])

        # 4. Authentication / Cookies
        b_idx = self.combo_browser_cookies.currentIndex()
        browser_map = {1: "brave", 2: "chrome", 3: "firefox", 4: "edge", 5: "opera", 6: "vivaldi"}
        if b_idx in browser_map:
            cmd.extend(["--cookies-from-browser", browser_map[b_idx]])

        custom_c = self.inp_cookies_file.text().strip()
        if custom_c and os.path.exists(custom_c):
            cmd.extend(["--cookies", custom_c])
        elif COOKIES_FILE.exists() and b_idx == 0:
            cmd.extend(["--cookies", str(COOKIES_FILE)])

        # 5. Metadata, Tags & Cover Art
        if self.chip_metadata.isChecked():
            cmd.append("--embed-metadata")
        if self.chip_thumbnail.isChecked():
            cmd.append("--embed-thumbnail")
        if self.chip_clean_tags.isChecked():
            cmd.extend(["--parse-metadata", "NA:description", "--parse-metadata", "NA:synopsis"])

        # 6. Subtitles
        if self.chk_embed_subs.isChecked():
            cmd.append("--embed-subs")
            if self.chk_auto_subs.isChecked():
                cmd.append("--write-auto-subs")

            lang_map = {
                0: "uk.*,en.*",
                1: "en.*",
                2: "uk.*",
                3: "all",
                4: "ru.*,en.*"
            }
            sub_lang = lang_map.get(self.combo_sub_lang.currentIndex(), "uk.*,en.*")
            cmd.extend(["--sub-langs", sub_lang])

            fmt_map = {0: "srt/best", 1: "vtt/best", 2: "ass/best"}
            cmd.extend(["--sub-format", fmt_map.get(self.combo_sub_fmt.currentIndex(), "srt/best")])

        # 7. Chapters & SponsorBlock
        if self.chk_embed_chapters.isChecked():
            cmd.append("--embed-chapters")
        if self.chk_split_chapters.isChecked():
            cmd.append("--split-chapters")

        sb_idx = self.combo_sponsorblock.currentIndex()
        if sb_idx == 1:
            cmd.extend(["--sponsorblock-remove", "sponsor,selfpromo,interaction,intro,outro"])
        elif sb_idx == 2:
            cmd.extend(["--sponsorblock-mark", "all"])

        # 8. Rate Limiting
        rate_map = {1: "10M", 2: "5M", 3: "2M", 4: "1M"}
        r_lim = rate_map.get(self.combo_speed_limit.currentIndex())
        if r_lim:
            cmd.extend(["-r", r_lim])

        # 9. Mode Specific Arguments
        checked_mode_btn = self.mode_group.checkedButton()
        mode = checked_mode_btn.property("mode_code") if checked_mode_btn else "video"

        # Codec sorting flag
        codec_pref = ""
        c_idx = self.combo_codec.currentIndex()
        if c_idx == 1:
            codec_pref = ",vcodec:h264"
        elif c_idx == 2:
            codec_pref = ",vcodec:av01,vp9"

        if mode == "video":
            q_idx = self.combo_quality.currentIndex()
            height_filters = {
                1: "[height<=1440]",
                2: "[height<=1080]",
                3: "[height<=720]",
                4: "[height<=480]",
                5: "[height<=360]"
            }
            h_filter = height_filters.get(q_idx, "")

            cont_text = self.combo_format.currentText().lower()
            container = "mp4"
            if "mkv" in cont_text:
                container = "mkv"
            elif "webm" in cont_text:
                container = "webm"
            elif "mov" in cont_text:
                container = "mov"

            if container == "mp4":
                # GUARANTEE 100% PLAYABLE AUDIO ON WINDOWS:
                # 1) Prefer MP4 video and M4A/AAC audio
                # 2) If audio happens to be Opus/Vorbis, FFmpeg lossless copy video and convert audio to AAC
                sort_str = f"res,ext:mp4:m4a{codec_pref}"
                cmd.extend([
                    "-o", "%(title)s.%(ext)s",
                    "--no-playlist",
                    "-f", f"bestvideo*{h_filter}+bestaudio/best{h_filter}",
                    "-S", sort_str,
                    "--merge-output-format", "mp4",
                    "--postprocessor-args", "Merger+ffmpeg:-c:v copy -c:a aac"
                ])
            else:
                # MKV / WebM natively support all modern codecs (Opus, VP9, AV1, etc.)
                cmd.extend([
                    "-o", "%(title)s.%(ext)s",
                    "--no-playlist",
                    "-f", f"bestvideo*{h_filter}+bestaudio/best{h_filter}",
                    "--merge-output-format", container
                ])

        elif mode == "audio":
            a_fmt = self.combo_audio_fmt.currentText().split()[0].lower()
            # Map quality index to bitrate / VBR
            q_idx = self.combo_audio_qual.currentIndex()
            qual_val = "0" if q_idx == 0 else ("1" if q_idx == 1 else ("2" if q_idx == 2 else "4"))

            cmd.extend([
                "-o", "%(title)s.%(ext)s",
                "--no-playlist",
                "-x",
                "--audio-format", a_fmt,
                "--audio-quality", qual_val
            ])

        elif mode == "video_only":
            q_idx = self.combo_quality.currentIndex()
            height_filters = {
                1: "[height<=1440]",
                2: "[height<=1080]",
                3: "[height<=720]",
                4: "[height<=480]",
                5: "[height<=360]"
            }
            h_filter = height_filters.get(q_idx, "")
            container = self.combo_format.currentText().split()[0].lower()

            cmd.extend([
                "-o", "%(title)s.%(ext)s",
                "--no-playlist",
                "-f", f"bestvideo*{h_filter}",
                "--remux-video", container
            ])

        elif mode == "playlist":
            is_audio = "Audio" in self.combo_format.currentText()
            p_range = self.inp_playlist_range.text().strip()

            if is_audio:
                cmd.extend([
                    "-o", "%(playlist_title)s/%(playlist_index)02d - %(title)s.%(ext)s",
                    "--yes-playlist",
                    "-x",
                    "--audio-format", "mp3",
                    "--audio-quality", "0"
                ])
            else:
                cmd.extend([
                    "-o", "%(playlist_title)s/%(playlist_index)02d - %(title)s.%(ext)s",
                    "--yes-playlist",
                    "-f", "bestvideo*+bestaudio/best",
                    "-S", "res,ext:mp4:m4a",
                    "--merge-output-format", "mp4",
                    "--postprocessor-args", "Merger+ffmpeg:-c:v copy -c:a aac"
                ])

            if p_range:
                cmd.extend(["--playlist-items", p_range])

        # 10. Arbitrary Custom Arguments
        custom = self.inp_custom_args.text().strip()
        if custom:
            import shlex
            try:
                cmd.extend(shlex.split(custom))
            except Exception:
                cmd.extend(custom.split())

        cmd.append(url)
        return cmd

    def start_download(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Missing URL", "Please enter a valid video or playlist URL.")
            return

        if not YT_DLP_EXE.exists():
            QMessageBox.critical(self, "Error", f"yt-dlp.exe not found at:\n{YT_DLP_EXE}")
            return

        dest_dir = Path(self.folder_input.text().strip() or DEFAULT_DOWNLOAD_DIR)
        dest_dir.mkdir(parents=True, exist_ok=True)

        self.save_current_settings()
        cmd = self.build_command(url)

        # UI state
        self.btn_download.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.btn_open_file.setEnabled(False)
        self.btn_open_file.setText("Open File")
        self.btn_open_file.setToolTip("")
        self.progress_bar.setValue(0)
        self.lbl_percent.setText("0%")
        self.lbl_status.setText("Connecting...")
        self.lbl_metrics.setText("")
        self.log_console.clear()

        self.download_worker = DownloadWorker(cmd, dest_dir)
        self.download_worker.progress_signal.connect(self.on_download_progress)
        self.download_worker.status_signal.connect(self.on_download_status)
        self.download_worker.log_signal.connect(self.on_download_log)
        self.download_worker.finished_signal.connect(self.on_download_finished)
        self.download_worker.start()

    def cancel_download(self):
        if self.download_worker and self.download_worker.isRunning():
            self.lbl_status.setText("Cancelling...")
            self.download_worker.cancel()

    def on_download_progress(self, pct: float, total_size: str, speed: str, eta: str):
        self.progress_bar.setValue(int(pct))
        self.lbl_percent.setText(f"{int(pct)}%")
        metrics = []
        if speed and speed != "—":
            metrics.append(speed)
        if eta and eta != "—":
            metrics.append(f"ETA {eta}")
        if total_size:
            metrics.append(total_size)
        self.lbl_metrics.setText(" • ".join(metrics))

    def on_download_status(self, text: str):
        self.lbl_status.setText(text)

    def on_download_log(self, line: str):
        self.log_console.append(line)
        sb = self.log_console.verticalScrollBar()
        sb.setValue(sb.maximum())

    def on_download_finished(self, success: bool, message: str):
        self.btn_download.setEnabled(True)
        self.btn_cancel.setEnabled(False)

        if success:
            self.progress_bar.setValue(100)
            self.lbl_percent.setText("100%")
            self.lbl_status.setText("Completed")
            self.lbl_metrics.setText("")

            target = message.strip() if message else ""
            if target and not os.path.isabs(target):
                dest_dir = Path(self.folder_input.text().strip() or DEFAULT_DOWNLOAD_DIR)
                target = str((dest_dir / target).resolve())

            if not target or not os.path.exists(target):
                dest_dir = Path(self.folder_input.text().strip() or DEFAULT_DOWNLOAD_DIR)
                if dest_dir.exists():
                    target = str(dest_dir.resolve())

            self.last_downloaded_target = target
            if target and os.path.exists(target):
                self.btn_open_file.setEnabled(True)
                if os.path.isfile(target):
                    self.btn_open_file.setText("Open File")
                    self.btn_open_file.setToolTip(f"Open: {os.path.basename(target)}\nRight-click for options")
                else:
                    self.btn_open_file.setText("Open Folder")
                    self.btn_open_file.setToolTip(f"Open folder: {target}\nRight-click for options")
        else:
            self.lbl_status.setText(f"Failed: {message}")
            self.lbl_metrics.setText("")

# ---------------------------------------------------------------------------
# Application Entry Point
# ---------------------------------------------------------------------------
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Otter")

    _, app_icon = create_monochrome_icons(APP_DIR)
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)

    window = OtterWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
