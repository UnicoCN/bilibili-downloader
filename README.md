# 🎬 Bilibili Video Downloader

<div align="center">

[![Python Version](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/github/license/mashape/apistatus.svg)](LICENSE)

A powerful python tool for downloading videos from [Bilibili](https://www.bilibili.com) with high quality.

</div>

## ✨ Features

- 📥 Download videos in highest quality available
- 🎵 Support for separate video and audio downloads
- 🚀 Parallel downloading for faster speeds
- 💾 Save video information in JSON format
- 🔄 Automatic merging of video and audio streams
- 📝 Detailed logging support

## 🚀 Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/bilibili-downloader.git
cd bilibili-downloader
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

## 📝 Prerequisites

- Python 3.7+
- FFmpeg installed and available in system PATH
- Bilibili account cookies (for accessing premium/high-quality content)

## 🎮 Usage

### Basic Usage

```bash
python bilibili_downloader.py -id <BV_ID>
```

### Command Line Options

```bash
Options:
  -id, --bvid       BV ID of the video (e.g., BV1xx411c7mD)
  -c, --cookie      Path to cookie file (default: cookie.txt)
  -o, --output      Output directory (default: output)
  --only-info       Only fetch video information without downloading
  --only-video      Download video stream only
  --only-audio      Download audio stream only
```

### Cookie File Format

Create a `cookie.txt` file containing your Bilibili SESSDATA cookie value:
```text
your_sessdata_cookie_value_here
```

### Examples

1. Download a video with default settings:
```bash
python bilibili_downloader.py -id BV1xx411c7mD
```

2. Download to a custom directory:
```bash
python bilibili_downloader.py -id BV1xx411c7mD -o ~/Downloads/bilibili
```

3. Only fetch video information:
```bash
python bilibili_downloader.py -id BV1xx411c7mD --only-info
```

## 📁 Output Structure

```
output/
├── uploader_name/
│   └── video_title.mp4
├── video_info.json
└── video_stream_info.json
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions, issues and feature requests are welcome!

## ⭐️ Show your support

Give a ⭐️ if this project helped you!
