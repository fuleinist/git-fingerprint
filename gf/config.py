import json
import os
from pathlib import Path


class Config:
    DEFAULT_DIR = ".gitfingerprint"
    CONFIG_FILE = "config.json"

    def __init__(self, repo_path: str | None = None):
        self.repo_path = Path(repo_path or os.getcwd())
        self.config_dir = self.repo_path / self.DEFAULT_DIR
        self.config_file = self.config_dir / self.CONFIG_FILE

    def ensure(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        if not self.config_file.exists():
            self._create_default()

    def _create_default(self) -> None:
        data = {
            "version": __version__,
            "last_analyzed": None,
            "commit_hash": None,
        }
        with open(self.config_file, "w") as f:
            json.dump(data, f, indent=2)

    def read(self) -> dict:
        self.ensure()
        with open(self.config_file) as f:
            return json.load(f)

    def write(self, data: dict) -> None:
        self.ensure()
        with open(self.config_file, "w") as f:
            json.dump(data, f, indent=2)
