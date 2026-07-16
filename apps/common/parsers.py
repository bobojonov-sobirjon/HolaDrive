"""Request parsers that tolerate non-UTF-8 JSON bodies (common with Windows clients/proxies)."""
from __future__ import annotations

import json

from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser


def _decode_json_bytes(raw: bytes) -> dict | list:
    if isinstance(raw, str):
        raw = raw.encode('utf-8', errors='replace')
    text = None
    last_err = None
    for enc in ('utf-8', 'utf-8-sig', 'cp1251', 'latin-1'):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError as exc:
            last_err = exc
            continue
    if text is None:
        text = raw.decode('utf-8', errors='replace')
    try:
        return json.loads(text)
    except (ValueError, TypeError) as exc:
        detail = f'JSON parse error - {exc}'
        if last_err:
            detail = f'{detail} (also encoding: {last_err})'
        raise ParseError(detail) from exc


class LenientJSONParser(JSONParser):
    """
    Always read raw bytes first, then decode with fallbacks.
    Avoids StreamReader UnicodeDecodeError on Windows-encoded bodies.
    """

    def parse(self, stream, media_type=None, parser_context=None):
        try:
            stream.seek(0)
        except Exception:
            pass
        raw = stream.read()
        try:
            return _decode_json_bytes(raw if raw is not None else b'')
        except ParseError:
            raise
        except Exception as exc:
            raise ParseError(f'JSON parse error - {exc}') from exc
