# 🎬 Bilibili Video Downloader

<div align="center">

[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/github/license/mashape/apistatus.svg)](LICENSE)

A simple Python tool for downloading high-quality videos from [Bilibili](https://www.bilibili.com).

</div>

## 🌟 Overview

Bilibili Video Downloader is a command-line tool that allows you to download videos from Bilibili with the best available quality. It handles video and audio streams separately and merges them for optimal quality.

### Key Features

- 🎥 Downloads videos in highest available quality
- 🔄 Parallel downloading of video and audio streams
- 🎵 Supports separate video/audio downloading
- 📊 Detailed video information extraction
- 📝 Comprehensive logging system
- 🚀 Fast and efficient processing

## 🛠️ Prerequisites

- Python 3.12 or higher
- FFmpeg (must be installed and accessible in system PATH)
- Valid Bilibili account cookies (for accessing restricted content)
- [uv](https://github.com/astral-sh/uv) 

## ⚡ Quick Start

1. **Install uv (if not already installed)**
   ```bash
   # On macOS and Linux.
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
   ```bash
   # On Windows.
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```
   ```bash
   # Or using pip
   pip install uv
   ```

2. **Clone the Repository**
   ```bash
   git clone https://github.com/UnicoCN/bilibili-downloader.git
   cd bilibili-downloader
   ```

3. **Install Dependencies**
   ```bash
   uv sync
   ```

4. **Configure Settings**
   - Copy `config/default.yaml` to `config/user.yaml`
   - Add your Bilibili cookie as "SESSDATA" to `user.yaml`

5. **Basic Usage**
   ```bash
   uv run main.py -id BV1xx411c7mD
   ```

## 🎮 Usage Guide

### Command Options

```bash
uv run main.py [OPTIONS]

Options:
  -id, --bvid TEXT     Bilibili video BV ID (Required)
  -o, --output PATH    Output directory [default: downloads/]
  --only-info          Only fetch video information
  --only-video         Download video stream only
  --only-audio         Download audio stream only
  -h, --help           Show this help message
```

### Advanced Examples

1. **Download to Custom Directory**
   ```bash
   uv run main.py -id BV1xx411c7mD -o ~/Videos/bilibili
   ```

2. **Extract Video Information Only**
   ```bash
   uv run main.py -id BV1xx411c7mD --only-info
   ```

3. **Download Audio Stream Only**
   ```bash
   uv run main.py -id BV1xx411c7mD --only-audio
   ```

## 📁 Project Structure

```
bilibili-downloader/
├── config/
│   ├── default.yaml   # Default configuration
│   └── user.yaml      # User-specific settings
├── downloads/         # Downloaded videos
├── logs/             # Application logs
├── src/              # Source code
├── data/             # Temporary data storage
├── pyproject.toml    # Project configuration and dependencies
└── uv.lock          # Dependency lock file
```

## 🔧 Configuration

### User Configuration (`config/user.yaml`)
```yaml
user:
  sessdata: "your_sessdata_cookie_here"
```

### Output Files
- Video files: `<downloads_path>/<uploader>/<title>.mp4`
- Video info: `<downloads_path>/video_info.json`
- Stream info: `<downloads_path>/video_stream_info.json`
- Logs: `<logs_path>/bilibili_downloader.log`

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⭐ Support

If you find this project helpful, please consider giving it a star ⭐ on GitHub!

## 📧 Contact

For bug reports or feature requests, please use the [GitHub Issues](https://github.com/yourusername/bilibili-downloader/issues) page.