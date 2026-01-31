# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A command-line tool for downloading videos from Bilibili with automatic quality selection and parallel downloading. Uses uv for dependency management and requires FFmpeg for video/audio merging.

## Development Commands

### Setup
```bash
# Install dependencies
uv sync

# Install with dev dependencies
uv sync --extra dev
```

### Running the Application
```bash
# Basic usage
uv run main.py -id BV1xx411c7mD

# With custom output directory
uv run main.py -id BV1xx411c7mD -o ~/Videos

# Only fetch video info (no download)
uv run main.py -id BV1xx411c7mD --only-info

# Download video or audio only
uv run main.py -id BV1xx411c7mD --only-video
uv run main.py -id BV1xx411c7mD --only-audio
```

### Testing
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/bilibili_downloader

# Run specific test file
uv run pytest tests/test_specific.py

# Run specific test function
uv run pytest tests/test_specific.py::test_function_name
```

### Linting and Type Checking
```bash
# Run ruff linter
uv run ruff check .

# Run ruff formatter
uv run ruff format .

# Run type checking with mypy
uv run mypy src/
```

## Architecture

### Core Components

1. **BilibiliDownloader** (`src/bilibili_downloader/bilibili_downloader.py`)
   - Main orchestrator class that coordinates the download process
   - Handles workflow: fetch video info → fetch stream info → parallel download → merge with FFmpeg
   - Manages temporary file cleanup after merging

2. **Config** (`src/bilibili_downloader/config.py`)
   - Manages configuration loading with deep merge strategy: `default.yaml` < `user.yaml` < env vars
   - SESSDATA priority: `BILIBILI_SESSDATA` env var > `user.yaml` > `default.yaml`
   - Validates FFmpeg availability at initialization
   - Provides helper methods for API URLs, headers, and file extensions

3. **Downloader Utils** (`src/bilibili_downloader/utils/downloader.py`)
   - `get_video_info()`: Fetches metadata (title, uploader, duration, cid)
   - `get_video_stream_info()`: Fetches DASH stream URLs with quality options
   - `download_file()`: Downloads with resume capability, retry logic with exponential backoff
   - `parallel_download()`: Uses ThreadPoolExecutor to download video/audio streams concurrently
   - Quality selection: Sorts streams by ID and bandwidth, selects highest quality

4. **Logger** (`src/bilibili_downloader/utils/logger.py`)
   - Rotating file handler with configurable size limits and backup counts

### Download Flow

1. Parse command-line arguments
2. Initialize Config (loads YAML, checks FFmpeg)
3. Initialize BilibiliDownloader
4. Fetch video metadata using BV ID
5. Extract CID and fetch DASH stream URLs
6. Sort streams by quality, select highest
7. Parallel download video.m4s and audio.m4s to `data/` directory
8. Merge streams with FFmpeg to `downloads/<uploader>/<title>.mp4`
9. Clean up temporary .m4s files

### Configuration System

- **default.yaml**: Contains API endpoints, paths, logging config, HTTP headers
- **user.yaml**: User overrides (primarily SESSDATA cookie)
- Deep merge: Nested dictionaries are merged recursively
- Environment variables take precedence over YAML files for SESSDATA

### API Integration

Uses two Bilibili endpoints:
- Video Info API: `https://api.bilibili.com/x/web-interface/view`
- Stream API: `https://api.bilibili.com/x/player/playurl` (requires SESSDATA cookie)

Stream API params: `qn=0` (all qualities), `fnval=80` (DASH format), `fourk=1` (4K if available)

### Error Handling

- Retry decorator with exponential backoff for network requests
- Resume capability for interrupted downloads using HTTP Range headers
- Validates downloaded file size matches Content-Length
- FFmpeg errors are caught and temporary files are cleaned up in finally block
- Missing SESSDATA raises RuntimeError with helpful instructions

## Key Technical Details

- **Python version**: Requires 3.12+
- **Package manager**: uv (Astral's fast Python package manager)
- **External dependency**: FFmpeg must be in system PATH
- **Parallel downloads**: Uses ThreadPoolExecutor with max_workers=2
- **Video format**: Downloads DASH streams (.m4s), merges to .mp4 with stream copy (no re-encoding)
- **Resume capability**: Uses HTTP Range headers and appends to partial files
- **Progress tracking**: tqdm for visual progress bars

## Testing Notes

- Tests should use pytest fixtures for mocking HTTP requests
- Use pytest-mock for mocking external dependencies (FFmpeg, filesystem)
- Mock the Config class to avoid requiring actual config files in tests
- Test both successful downloads and error scenarios (network failures, missing files, FFmpeg errors)
