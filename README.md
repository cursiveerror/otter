# 🦦 Otter

A minimalist, high-performance desktop GUI client for [yt-dlp](https://github.com/yt-dlp/yt-dlp) built with Python and PyQt6, featuring a modern monochrome aesthetic.

![Otter Interface](otter_icon_desktop.png)

## ✨ Features

- **Multi-Mode Support**: Download Video + Audio, Audio Only (MP3/FLAC/M4A/WAV), Video Only, or Full Playlists with custom item ranges.
- **Audio & Video Formats**: Flexible quality selection up to 4K / 2160p, MP4 (Universal AAC), MKV, WebM, and audio bitrates up to 320 kbps.
- **Sound & Codec Fixes**: Optimized stream merging with FFmpeg AAC postprocessing ensuring compatibility with Windows Media Player and default players.
- **Turbo Fragments**: Multi-threaded parallel stream chunk downloading (`-N 4`) for maximum bandwidth utilization.
- **Advanced yt-dlp Controls**:
  - Subtitle embedding (auto-generated & multi-language).
  - Chapters embedding & chapter splitting.
  - SponsorBlock integration (automatic sponsor removal or chapter marking).
  - Browser cookie extraction (Chrome, Brave, Firefox, Edge, Opera, Vivaldi) and custom `cookies.txt` support to bypass age or login restrictions.
  - Bandwidth rate limits and arbitrary custom CLI arguments.
- **Auto-Updates**: Automatically checks, updates, or downloads `yt-dlp.exe` on startup.
- **Monochrome Dark Design**: Pure Linear/Nothing OS dark aesthetics, native Windows 11 immersive dark titlebar, and smooth interactive feedback.

## 🚀 Quick Start (Pre-built Executable)

Download the latest `Otter.exe` from the **[Releases](https://github.com/)** tab.  
Drop it into any folder and run. If `yt-dlp.exe` isn't found, Otter will automatically download the latest version for you.

## 🛠️ Running from Source

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/otter.git
   cd otter
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run Otter**:
   ```bash
   python otter.py
   ```

## 📦 Building Standalone `.exe`

To package Otter into a standalone Windows executable:

```bash
pip install pyinstaller
python -m PyInstaller --noconfirm --clean --windowed --onefile --icon="otter_icon_desktop.ico" --name="Otter" --add-data "otter_icon_main.png;." --add-data "otter_icon_main.svg;." --add-data "otter_icon_desktop.png;." --add-data "otter_icon_desktop.ico;." --add-data "otter_icon_desktop.svg;." --hidden-import="PyQt6.QtSvg" otter.py
```

The compiled binary will be located in the `dist/Otter.exe` folder.

## 📄 License

MIT License.
