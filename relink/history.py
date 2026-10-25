"""Bounded local JSON history. Never stores PDFs, unpickles, or makes requests."""
from __future__ import annotations
from dataclasses import asdict, dataclass, fields, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from functools import lru_cache
from pathlib import Path
from threading import RLock
from types import UnionType
from typing import get_args, get_origin, get_type_hints
import json
import os
import tempfile
import uuid

from relink.paper_models import Paper, PaperDatasetLookup, PaperSearchResult
from relink.workflow import RecoveryReport


MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_ENTRY_BYTES = 2 * 1024 * 1024
RESULT_TYPES = {'recovery': RecoveryReport, 'papers': PaperSearchResult, 'paper_datasets': PaperDatasetLookup}
_LOCK = RLock()


class HistoryError(ValueError):
    """History is unavailable/invalid; current search results remain usable."""


@dataclass(frozen=True)
class HistoryEntry:
    id: str
    kind: str
    created_at: str
    label: str
    snapshot: dict
    request: dict


def _reject_constant(value):
    raise ValueError('Non-finite JSON value: ' + value)


def _json_bytes(value) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')
    except (TypeError, ValueError, RecursionError) as exc:
        raise HistoryError('History must contain bounded JSON data, not files or binary content.') from exc


@lru_cache(maxsize=32)
def _hints(annotation):
    return get_type_hints(annotation)


def _decode(value, annotation, depth=0):
    """Decode declared dataclass fields only; types are supplied by our code."""
    if depth > 30:
        raise HistoryError('History data is too deeply nested.')
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is UnionType:
        for option in args:
            try: return _decode(value, option, depth + 1)
            except (HistoryError, ValueError, TypeError): pass
        raise HistoryError('History field has an invalid type.')
    if origin is tuple:
        if not isinstance(value, list) or len(value) > 10000:
            raise HistoryError('History tuple is invalid or too large.')
        return tuple(_decode(item, args[0], depth + 1) for item in value)
    if isinstance(annotation, type) and is_dataclass(annotation):
        if not isinstance(value, dict): raise HistoryError('Expected a history object.')
        declared = {field.name for field in fields(annotation)}
        if set(value) - declared: raise HistoryError('History contains unknown fields.')
        hints = _hints(annotation)
        return annotation(**{name: _decode(item, hints[name], depth + 1) for name, item in value.items()})
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return annotation(value)
    if annotation is dict:
        if not isinstance(value, dict): raise HistoryError('Expected a history dictionary.')
        _check_json(value, depth)
        return value
    if annotation is type(None) and value is None: return None
    if annotation in (str, int, bool) and type(value) is annotation: return value
    raise HistoryError('Invalid history field type.')


def _check_json(value, depth=0):
    if depth > 30: raise HistoryError('History data is too deeply nested.')
    if isinstance(value, dict):
        if len(value) > 10000 or not all(isinstance(key, str) for key in value):
            raise HistoryError('Invalid history dictionary.')
        for item in value.values(): _check_json(item, depth + 1)
    elif isinstance(value, list):
        if len(value) > 10000: raise HistoryError('History list is too long.')
        for item in value: _check_json(item, depth + 1)
    elif value is not None and type(value) not in (str, int, float, bool):
        raise HistoryError('History contains unsupported values.')


def restore_snapshot(entry: HistoryEntry):
    try:
        result_type = RESULT_TYPES[entry.kind]
        return _decode(entry.snapshot, result_type)
    except (KeyError, ValueError, TypeError, RecursionError) as exc:
        raise HistoryError('Saved results are invalid or incompatible with this version.') from exc


def restore_paper(entry: HistoryEntry) -> Paper:
    try: return _decode(entry.request['paper'], Paper)
    except (KeyError, ValueError, TypeError, RecursionError) as exc:
        raise HistoryError('The saved paper request cannot be restored.') from exc


def _validate_entry(entry):
    if not all(isinstance(value, str) for value in (entry.id, entry.kind, entry.created_at, entry.label)):
        raise HistoryError('Invalid history entry fields.')
    uuid.UUID(entry.id)
    if len(entry.label) > 2000 or datetime.fromisoformat(entry.created_at).tzinfo is None:
        raise HistoryError('Invalid history label or timestamp.')
    if not isinstance(entry.request, dict): raise HistoryError('Invalid saved request.')
    _check_json(entry.request)
    if entry.kind == 'papers':
        if not isinstance(entry.request.get('topic'), str) or not 1 <= len(entry.request['topic']) <= 1200:
            raise HistoryError('Invalid saved paper topic.')
    elif entry.kind == 'paper_datasets': restore_paper(entry)
    restore_snapshot(entry)


def prepare_entry(kind: str, label: str, result, *, request: dict | None = None) -> HistoryEntry:
    """Build a validated snapshot even when persistence is unavailable."""
    if kind not in RESULT_TYPES or not isinstance(result, RESULT_TYPES[kind]):
        raise HistoryError('Unsupported history result type.')
    if not isinstance(label, str) or len(label) > 2000: raise HistoryError('History label is too long.')
    entry = HistoryEntry(str(uuid.uuid4()), kind, datetime.now(timezone.utc).isoformat(), label,
                         asdict(result), request or {})
    plain = _json_bytes(asdict(entry))
    if len(plain) > MAX_ENTRY_BYTES: raise HistoryError('This result is too large to save in history.')
    entry = HistoryEntry(**json.loads(plain))
    try: _validate_entry(entry)
    except (ValueError, TypeError, KeyError, RecursionError) as exc:
        raise HistoryError('Invalid history entry.') from exc
    return entry


class HistoryStore:
    """One local workspace store, with atomic writes and in-process serialization."""
    def __init__(self, path: str | Path, *, max_entries: int = 50):
        if type(max_entries) is not int or not 1 <= max_entries <= 50:
            raise HistoryError('History limit must be 1–50 entries.')
        self.path = Path(path)
        self.max_entries = max_entries

    def _read(self) -> list[HistoryEntry]:
        try:
            if not self.path.exists(): return []
            with self.path.open('rb') as source:
                raw = source.read(MAX_FILE_BYTES + 1)
            if len(raw) > MAX_FILE_BYTES: raise HistoryError('History file exceeds its size limit.')
            payload = json.loads(raw, parse_constant=_reject_constant)
            if not isinstance(payload, dict) or type(payload.get('version')) is not int or payload['version'] != 1:
                raise HistoryError('Unsupported history format.')
            rows = payload.get('entries')
            if not isinstance(rows, list) or len(rows) > 50:
                raise HistoryError('Invalid history entries.')
            entries, seen = [], set()
            for row in rows:
                if len(_json_bytes(row)) > MAX_ENTRY_BYTES: raise HistoryError('History entry is too large.')
                if not isinstance(row, dict): raise HistoryError('Invalid history entry.')
                entry = HistoryEntry(**row)
                _validate_entry(entry)
                if entry.id in seen: raise HistoryError('Repeated history entry ID.')
                seen.add(entry.id)
                entries.append(entry)
            return entries
        except HistoryError: raise
        except (OSError, ValueError, TypeError, KeyError, RecursionError, UnicodeError) as exc:
            raise HistoryError('History file could not be read; it was not replaced.') from exc

    def list(self) -> list[HistoryEntry]:
        with _LOCK: return self._read()

    def _write(self, entries: list[HistoryEntry]):
        data = _json_bytes({'version': 1, 'entries': [asdict(entry) for entry in entries]})
        while len(data) > MAX_FILE_BYTES and len(entries) > 1:
            entries.pop()
            data = _json_bytes({'version': 1, 'entries': [asdict(entry) for entry in entries]})
        temporary = None
        try:
            self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            descriptor, temporary = tempfile.mkstemp(prefix='.history-', suffix='.tmp', dir=self.path.parent)
            with os.fdopen(descriptor, 'wb') as output:
                output.write(data)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, self.path)
        except OSError as exc:
            raise HistoryError('History could not be saved; existing results remain available.') from exc
        finally:
            if temporary:
                try: Path(temporary).unlink(missing_ok=True)
                except OSError: pass

    def add(self, kind: str, label: str, result, *, request: dict | None = None) -> HistoryEntry:
        entry = prepare_entry(kind, label, result, request=request)
        with _LOCK:
            entries = self._read()
            self._write(([entry] + entries)[:self.max_entries])
        return entry

    def delete(self, entry_id: str):
        with _LOCK: self._write([entry for entry in self._read() if entry.id != entry_id])

    def clear(self):
        with _LOCK: self._write([])
