import yaml
from pathlib import Path
from typing import Dict, Any
import shutil

class Config:
    def __init__(self, root_path: Path):
        self.root_dir: Path = root_path
        self.config_dir = self.root_dir / "config"
        self.load_config()  # Load config first
        self._setup_paths()  # Then setup paths using config values
        self.setup_directories()
        self._check_dependencies()

    def _setup_paths(self) -> None:
        """Setup all path attributes using config values"""
        self.data_dir = self.root_dir / self.config['paths']['data']
        self.downloads_dir = self.root_dir / self.config['paths']['downloads']
        self.logs_dir = self.root_dir / self.config['paths']['logs']

    def load_config(self) -> None:
        """Load configuration from YAML files"""
        default_config = self.config_dir / "default.yaml"
        user_config = self.config_dir / "user.yaml"

        if not default_config.exists():
            raise FileNotFoundError(f"Default config not found: {default_config}")

        with open(default_config, 'r') as f:
            self.config = yaml.safe_load(f)

        if user_config.exists():
            with open(user_config, 'r') as f:
                user_settings = yaml.safe_load(f)
                self._deep_update(self.config, user_settings)

    def _deep_update(self, d: Dict, u: Dict) -> None:
        """Recursively update nested dictionaries for merging user.yaml into default.yaml"""
        for k, v in u.items():
            if k in d and isinstance(d[k], dict) and isinstance(v, dict):
                self._deep_update(d[k], v)
            else:
                d[k] = v

    def setup_directories(self) -> None:
        """Create necessary directories"""
        dirs = [self.data_dir, self.downloads_dir, self.logs_dir]
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)

    def _check_dependencies(self) -> None:
        """Check if required external dependencies are available"""
        if not shutil.which('ffmpeg'):
            raise RuntimeError("FFmpeg is not installed or not in PATH")

    def get_api_url(self, name: str) -> str:
        """Get API URL by name"""
        return self.config['api'][name]

    @property
    def log_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        return self.config['logging']

    @property
    def sessdata(self) -> str:
        """Get SESSDATA from user config"""
        return self.config['user']['sessdata']

    def get_file_extension(self, name: str) -> str:
        """Get file extension by name"""
        return self.config['file']['extensions'][name]
    
    def get_http_header(self, name: str) -> str:
        """Get HTTP header by name"""
        return self.config['http']['headers'][name]
    
    def get_headers_for_video(self, bv_id: str = "") -> Dict[str, str]:
        """Get common HTTP headers for video requests"""
        headers = {
            "User-Agent": self.get_http_header("user_agent"),
            "Referer": f"{self.get_http_header('referer')}/video/{bv_id}" if bv_id else self.get_http_header("referer"),
            "Origin": self.get_http_header("origin")
        }
        return headers
