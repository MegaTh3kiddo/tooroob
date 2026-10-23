import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, ConfigDict, Field

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader (KEY=VALUE lines). Real environment variables always win."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(PROJECT_ROOT / ".env")

class AppSettings(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    app_name: str = "Torob Intelligence Engine"
    app_version: str = "1.0.0"
    environment: str = Field(default_factory=lambda: os.getenv("TOROB_ENV", "development"))
    debug: bool = Field(default_factory=lambda: os.getenv("TOROB_DEBUG", "false").lower() == "true")
    
    # Paths
    project_root: Path = PROJECT_ROOT
    data_dir: Path = PROJECT_ROOT / "data"
    config_dir: Path = PROJECT_ROOT / "configs"
    policy_path: Path = PROJECT_ROOT / "configs" / "policy.yaml"
    
    # Database
    duckdb_path: str = Field(default_factory=lambda: os.getenv("TOROB_DUCKDB_PATH", ":memory:"))
    sqlite_path: Path = Field(default_factory=lambda: Path(os.getenv("TOROB_SQLITE_PATH", str(PROJECT_ROOT / "data" / "torob_ledger.db"))))

    # Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: List[str] = Field(
        default_factory=lambda: [
            o.strip()
            for o in os.getenv(
                "TOROB_CORS_ORIGINS",
                "http://localhost:3000,http://localhost:5173,http://localhost:8080,http://127.0.0.1:3000,http://127.0.0.1:5173,http://127.0.0.1:8080",
            ).split(",")
            if o.strip()
        ]
    )


def load_policy(path: Optional[Path] = None) -> Dict[str, Any]:
    policy_file = path or (PROJECT_ROOT / "configs" / "policy.yaml")
    if not policy_file.exists():
        # Fallback to empty config if file is missing
        return {}
    with open(policy_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


settings = AppSettings()
