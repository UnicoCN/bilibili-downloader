# Bilibili Downloader

<div align="center">

**A fast, simple CLI tool for downloading high-quality videos from Bilibili.**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-3776ab.svg?style=flat&logo=python&logoColor=white)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

</div>

---

## Features

- **Highest Quality** — Automatically selects the best available video and audio streams
- **Parallel Downloads** — Downloads video and audio streams concurrently
- **Resume Support** — Interrupted downloads can be resumed automatically
- **Flexible Output** — Download video only, audio only, or both merged

## Requirements

- Python 3.12+
- [FFmpeg](https://ffmpeg.org/) in system PATH
- [uv](https://github.com/astral-sh/uv) package manager
- Bilibili SESSDATA cookie

## Installation

```bash
# Clone the repository
git clone https://github.com/UnicoCN/bilibili-downloader.git
cd bilibili-downloader

# Install dependencies
uv sync
```

## Configuration

Set your Bilibili SESSDATA cookie using **one** of the following methods:

**Option 1: Environment variable** (recommended)
```bash
export BILIBILI_SESSDATA="your_sessdata_here"
```

**Option 2: Config file**
```bash
cp config/default.yaml config/user.yaml
```
Then edit `config/user.yaml`:
```yaml
user:
  sessdata: "your_sessdata_here"
```

## Usage

```bash
# Basic download
uv run main.py -id BV1xx411c7mD

# Custom output directory
uv run main.py -id BV1xx411c7mD -o ~/Videos

# Fetch video info only (no download)
uv run main.py -id BV1xx411c7mD --only-info

# Download video or audio only
uv run main.py -id BV1xx411c7mD --only-video
uv run main.py -id BV1xx411c7mD --only-audio
```

### Options

| Option | Description |
|--------|-------------|
| `-id, --bvid` | Bilibili video BV ID (required) |
| `-o, --output` | Output directory (default: `downloads/`) |
| `--only-info` | Only fetch video information |
| `--only-video` | Download video stream only |
| `--only-audio` | Download audio stream only |

## Output

```
downloads/
└── <uploader>/
    └── <title>.mp4
```

## Development

```bash
# Install dev dependencies
uv sync --extra dev

# Run tests
uv run pytest

# Lint & format
uv run ruff check .
uv run ruff format .

# Type check
uv run mypy src/
```

## License

MIT
