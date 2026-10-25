"""Server-side credentials; never serialize configuration into reports/history."""
from dataclasses import dataclass, field
import os
from pathlib import Path
import re
import tomllib


DEFAULT_MODEL = 'gemini-3.5-flash-lite'


@dataclass(frozen=True)
class GeminiSettings:
    api_key: str = field(default='', repr=False)
    model: str = DEFAULT_MODEL


def load_gemini_settings(secret_path: Path | None = None) -> GeminiSettings:
    key = os.environ.get('GEMINI_API_KEY', '')
    model = os.environ.get('GEMINI_MODEL', '')
    if not key:
        path = secret_path or Path(__file__).resolve().parents[1] / '.streamlit' / 'secrets.toml'
        try:
            with path.open('rb') as source: data = tomllib.load(source)
            key = data.get('GEMINI_API_KEY', '')
            model = model or data.get('GEMINI_MODEL', '')
        except (OSError, ValueError):
            return GeminiSettings()
    if not isinstance(key, str) or len(key) > 512 or any(ord(c) <= 32 for c in key):
        key = ''
    if not isinstance(model, str) or not re.fullmatch(r'gemini-[a-zA-Z0-9._-]{1,70}', model):
        model = DEFAULT_MODEL
    return GeminiSettings(key, model)
