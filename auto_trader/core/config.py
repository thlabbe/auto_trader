"""Database path configuration."""
import os
from pathlib import Path


def get_db_path() -> Path:
    env_path = os.environ.get('AUTO_TRADER_DB_PATH')
    if env_path:
        return Path(env_path)
    default = Path.home() / '.auto_trader' / 'data.db'
    default.parent.mkdir(parents=True, exist_ok=True)
    return default
