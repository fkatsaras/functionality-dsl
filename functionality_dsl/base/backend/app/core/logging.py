from __future__ import annotations

import json
import logging
import sys
import time
import contextvars


request_id_cv = contextvars.ContextVar("request_id", default="-")

class JsonFormatter(logging.Formatter):
    def __init__(self, fmt = None, datefmt = None, style = "%", validate = True, *, defaults = None, static = None):
        super().__init__(fmt, datefmt, style, validate, defaults=defaults)
        self.static = dict(static or {})
        
    def format(self, record: logging.LogRecord) -> str:
        # base
        payload = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
            "lvl": record.levelname.lower(),
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id_cv.get(None),
        }
        # extras (anything set via `extra=...`)
        for k, v in record.__dict__.items():
            if k in ("args","asctime","created","exc_info","exc_text","filename","funcName",
                     "levelname","levelno","lineno","module","msecs","msg","name","pathname",
                     "process","processName","relativeCreated","stack_info","thread","threadName"):
                continue
            payload[k] = v
        # merge statics last (won't overwrite explicit keys)
        for k, v in self.static.items():
            payload.setdefault(k, v)

        if record.exc_info:
            payload["exc_type"] = record.exc_info[0].__name__
            payload["exc"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)
    
def configure_logging(level: str = "INFO", *, json_mode: bool = True):
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)
    if json_mode:
        handler.setFormatter(JsonFormatter(static={"app": "fdsl-backend"}))
    else:
        fmt = "%(levelname)s %(name)s %(message)s"
        handler.setFormatter(logging.Formatter(fmt))
    root.addHandler(handler)

def set_request_id(value: str) -> None:
    request_id_cv.set(value)