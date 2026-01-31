"""Unit tests for config module."""
import os
import tempfile
from pathlib import Path
import pytest
import yaml

from src.bilibili_downloader.config import Config


class TestConfig:
    """Test cases for Config class."""

    def test_config_loads_default(self, tmp_path):
        """Test that default config loads successfully."""
        # Create temporary config directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        default_config = {
            'api': {
                'video_info': 'https://api.bilibili.com/x/web-interface/view',
                'video_stream': 'https://api.bilibili.com/x/player/playurl'
            },
            'paths': {
                'downloads': 'downloads',
                'logs': 'logs',
                'data': 'data'
            },
            'logging': {
                'filename': 'bilibili_downloader.log',
                'max_size': 5242880,
                'backup_count': 3,
                'format': '%(asctime)s - %(levelname)s - %(message)s'
            },
            'file': {
                'extensions': {
                    'video': '.m4s',
                    'audio': '.m4s',
                    'output': '.mp4'
                }
            },
            'http': {
                'headers': {
                    'user_agent': 'Mozilla/5.0',
                    'referer': 'https://www.bilibili.com',
                    'origin': 'https://www.bilibili.com'
                }
            },
            'user': {
                'sessdata': ''
            }
        }

        with open(config_dir / "default.yaml", 'w') as f:
            yaml.dump(default_config, f)

        config = Config(tmp_path)

        assert config.config is not None
        assert config.get_api_url('video_info') == 'https://api.bilibili.com/x/web-interface/view'
        assert config.get_file_extension('output') == '.mp4'

    def test_config_deep_update(self, tmp_path):
        """Test that user config properly overrides default config."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        default_config = {
            'api': {'video_info': 'https://api.bilibili.com/test'},
            'user': {'sessdata': ''},
            'paths': {'downloads': 'downloads', 'logs': 'logs', 'data': 'data'},
            'logging': {'filename': 'test.log', 'max_size': 100, 'backup_count': 1, 'format': 'test'},
            'file': {'extensions': {'video': '.m4s', 'audio': '.m4s', 'output': '.mp4'}},
            'http': {'headers': {'user_agent': 'test', 'referer': 'test', 'origin': 'test'}}
        }

        user_config = {
            'user': {'sessdata': 'test_sessdata_value'}
        }

        with open(config_dir / "default.yaml", 'w') as f:
            yaml.dump(default_config, f)

        with open(config_dir / "user.yaml", 'w') as f:
            yaml.dump(user_config, f)

        config = Config(tmp_path)

        # sessdata should be from user config
        assert config.config['user']['sessdata'] == 'test_sessdata_value'
        # paths should still be from default
        assert config.config['paths']['downloads'] == 'downloads'

    def test_sessdata_priority_env_over_config(self, tmp_path, monkeypatch):
        """Test that environment variable takes priority over config file."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        default_config = {
            'api': {'video_info': 'test'},
            'paths': {'downloads': 'downloads', 'logs': 'logs', 'data': 'data'},
            'logging': {'filename': 'test.log', 'max_size': 100, 'backup_count': 1, 'format': 'test'},
            'file': {'extensions': {'video': '.m4s', 'audio': '.m4s', 'output': '.mp4'}},
            'http': {'headers': {'user_agent': 'test', 'referer': 'test', 'origin': 'test'}},
            'user': {'sessdata': 'config_sessdata'}
        }

        with open(config_dir / "default.yaml", 'w') as f:
            yaml.dump(default_config, f)

        # Set environment variable
        monkeypatch.setenv('BILIBILI_SESSDATA', 'env_sessdata')

        config = Config(tmp_path)

        # Environment variable should take priority
        assert config.sessdata == 'env_sessdata'

    def test_sessdata_fallback_to_config(self, tmp_path, monkeypatch):
        """Test that config file is used when env var is not set."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        default_config = {
            'api': {'video_info': 'test'},
            'paths': {'downloads': 'downloads', 'logs': 'logs', 'data': 'data'},
            'logging': {'filename': 'test.log', 'max_size': 100, 'backup_count': 1, 'format': 'test'},
            'file': {'extensions': {'video': '.m4s', 'audio': '.m4s', 'output': '.mp4'}},
            'http': {'headers': {'user_agent': 'test', 'referer': 'test', 'origin': 'test'}},
            'user': {'sessdata': 'config_sessdata'}
        }

        with open(config_dir / "default.yaml", 'w') as f:
            yaml.dump(default_config, f)

        # Ensure env var is not set
        monkeypatch.delenv('BILIBILI_SESSDATA', raising=False)

        config = Config(tmp_path)

        # Should fall back to config file
        assert config.sessdata == 'config_sessdata'

    def test_directories_created(self, tmp_path):
        """Test that necessary directories are created."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        default_config = {
            'api': {'video_info': 'test'},
            'paths': {'downloads': 'downloads', 'logs': 'logs', 'data': 'data'},
            'logging': {'filename': 'test.log', 'max_size': 100, 'backup_count': 1, 'format': 'test'},
            'file': {'extensions': {'video': '.m4s', 'audio': '.m4s', 'output': '.mp4'}},
            'http': {'headers': {'user_agent': 'test', 'referer': 'test', 'origin': 'test'}},
            'user': {'sessdata': ''}
        }

        with open(config_dir / "default.yaml", 'w') as f:
            yaml.dump(default_config, f)

        config = Config(tmp_path)

        assert config.data_dir.exists()
        assert config.downloads_dir.exists()
        assert config.logs_dir.exists()

    def test_get_headers_for_video(self, tmp_path):
        """Test that video headers are generated correctly."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        default_config = {
            'api': {'video_info': 'test'},
            'paths': {'downloads': 'downloads', 'logs': 'logs', 'data': 'data'},
            'logging': {'filename': 'test.log', 'max_size': 100, 'backup_count': 1, 'format': 'test'},
            'file': {'extensions': {'video': '.m4s', 'audio': '.m4s', 'output': '.mp4'}},
            'http': {
                'headers': {
                    'user_agent': 'Mozilla/5.0',
                    'referer': 'https://www.bilibili.com',
                    'origin': 'https://www.bilibili.com'
                }
            },
            'user': {'sessdata': ''}
        }

        with open(config_dir / "default.yaml", 'w') as f:
            yaml.dump(default_config, f)

        config = Config(tmp_path)
        headers = config.get_headers_for_video('BV1xx411c7mD')

        assert headers['User-Agent'] == 'Mozilla/5.0'
        assert headers['Referer'] == 'https://www.bilibili.com/video/BV1xx411c7mD'
        assert headers['Origin'] == 'https://www.bilibili.com'
