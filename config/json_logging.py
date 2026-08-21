"""Minimal JSON log formatter (no extra dependency)."""
import json
import logging
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            'level': record.levelname,
            'time': datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            'logger': record.name,
            'module': record.module,
            'message': record.getMessage(),
        }
        if getattr(record, 'request_id', None):
            payload['request_id'] = record.request_id
        if record.exc_info:
            payload['exc'] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)
