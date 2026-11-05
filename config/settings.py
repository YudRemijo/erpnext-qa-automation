"""Local settings: process environment takes precedence over an optional .env.

The dependency-free file format accepts KEY=value, blank lines, full-line
comments, and optional matching single/double quotes around a value.
Interpolation, escape processing, and inline comments are not supported.
Values are never copied into os.environ or included in error messages.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SETTING_NAMES = (
    "ERPNEXT_BASE_URL",
    "ERPNEXT_USERNAME",
    "ERPNEXT_PASSWORD",
)


def _read_local_env(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}

    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8-sig").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        key = key.strip()
        if not separator:
            raise ValueError(f"Invalid .env assignment on line {line_number}.")
        if key not in SETTING_NAMES:
            continue
        value = value.strip()
        if value.startswith(("'", '"')):
            if len(value) < 2 or value[-1] != value[0]:
                raise ValueError(f"Unclosed .env quote on line {line_number}.")
            value = value[1:-1]
        if key in values:
            raise ValueError(f"Duplicate .env setting on line {line_number}.")
        values[key] = value
    return values


@dataclass(frozen=True)
class Settings:
    base_url: str
    username: str = field(repr=False)
    password: str = field(repr=False)

    @classmethod
    def load(cls, env_file: Path | None = None) -> "Settings":
        """Load on demand; never read credentials merely by importing this module."""
        local_values = _read_local_env(
            PROJECT_ROOT / ".env" if env_file is None else env_file
        )
        values = {
            name: os.environ[name] if name in os.environ else local_values.get(name, "")
            for name in SETTING_NAMES
        }
        values["ERPNEXT_BASE_URL"] = values["ERPNEXT_BASE_URL"].strip()
        missing = [name for name, value in values.items() if not value.strip()]
        if missing:
            raise ValueError("Missing required settings: " + ", ".join(missing))
        if values["ERPNEXT_PASSWORD"] == "REPLACE_WITH_LOCAL_PASSWORD":
            raise ValueError("Replace the local password placeholder before use.")

        base_url = values["ERPNEXT_BASE_URL"].rstrip("/")
        try:
            parsed = urlsplit(base_url)
            valid = (
                parsed.scheme in {"http", "https"}
                and bool(parsed.hostname)
                and not parsed.username
                and not parsed.password
                and not parsed.query
                and not parsed.fragment
            )
        except ValueError:
            valid = False
        if not valid:
            raise ValueError("ERPNEXT_BASE_URL must be an HTTP(S) URL without credentials, query, or fragment.")

        return cls(
            base_url=base_url,
            username=values["ERPNEXT_USERNAME"],
            password=values["ERPNEXT_PASSWORD"],
        )
