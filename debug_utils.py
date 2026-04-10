import functools
import logging
import os
import time
import sys
from collections.abc import Callable
from types import FrameType
from typing import Any, ParamSpec, TypeVar, cast

try:
    import psutil  # type: ignore[import-untyped]
except ImportError:
    psutil = None

from pathlib import Path

P = ParamSpec("P")
R = TypeVar("R")

_SENSITIVE_NAME_TOKENS = {
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "auth",
    "credential",
    "clipboard",
    "pii",
    "email",
    "phone",
}


def _sanitize_trace_value(name: str, value: object) -> str:
    """Return a safe, length-limited representation for trace logging."""
    lowered_name = name.lower()
    if any(token in lowered_name for token in _SENSITIVE_NAME_TOKENS):
        return "<masked>"

    try:
        value_repr = repr(value)
    except Exception:
        return "<unrepresentable>"

    lowered_value = value_repr.lower()
    if any(token in lowered_value for token in _SENSITIVE_NAME_TOKENS):
        return "<masked>"
    if "bearer " in lowered_value or "sk-" in lowered_value:
        return "<masked>"

    if len(value_repr) > 100:
        return value_repr[:97] + "..."
    return value_repr


def ensure_project_temp(root: Path) -> Path:
    """Ensures the project temp directory exists."""
    temp_dir = root / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def is_debug_enabled() -> bool:
    return os.getenv("AI_LAN_DEBUG", "0") == "1"


def is_trace_enabled() -> bool:
    return os.getenv("AI_LAN_TRACE", "0") == "1"


def is_profile_enabled() -> bool:
    return os.getenv("AI_LAN_PROFILE", "0") == "1"


def _setup_logger() -> logging.Logger:
    logger = logging.getLogger("sentinel")
    if not logger.hasHandlers():
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        log_file = os.getenv("AI_LAN_DEBUG_LOGFILE")
        if log_file:
            # Automatic log size maintenance (1GB limit)
            MAX_BYTES = 1024 * 1024 * 1024  # 1GB
            if os.path.exists(log_file) and os.path.getsize(log_file) > MAX_BYTES:
                with open(log_file, "w", encoding="utf-8"):
                    pass
            fh = logging.FileHandler(log_file, mode="a", encoding="utf-8")
            fh.setFormatter(formatter)
            logger.addHandler(fh)
        else:
            sh = logging.StreamHandler(sys.stdout)
            sh.setFormatter(formatter)
            logger.addHandler(sh)
    return logger


def sentinel_trace_func(frame: FrameType, event: str, arg: object) -> Any:
    _ = arg
    if event == "line":
        line_no = frame.f_lineno
        vars = frame.f_locals
        # Log local variables at this line
        logger = _setup_logger()
        for name, value in vars.items():
            try:
                val_repr = _sanitize_trace_value(name, value)
                msg = f"[TRACE] line {line_no}: {name} = {val_repr}"
                logger.debug(msg)
                # Only print to stdout if explicitly requested to avoid terminal flooding
                if os.getenv("AI_LAN_TRACE_STDOUT", "0") == "1":
                    print(msg)
            except Exception:
                pass
    return sentinel_trace_func


def sentinel(func: Callable[P, R]) -> Callable[P, R]:
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        logger = _setup_logger()
        if is_debug_enabled():
            logger.debug(f"[SENTINEL] Enter {func.__qualname__}")

        # Profiling Start
        start_time = time.perf_counter()
        process = psutil.Process(os.getpid()) if psutil is not None else None
        mem_start = process.memory_info().rss / (1024 * 1024) if process is not None else 0.0

        if is_trace_enabled():
            sys.settrace(cast(Any, sentinel_trace_func))

        try:
            result: R = func(*args, **kwargs)
            return result
        finally:
            if is_trace_enabled():
                sys.settrace(None)

            # Profiling End
            duration = (time.perf_counter() - start_time) * 1000
            mem_end = (
                process.memory_info().rss / (1024 * 1024) if process is not None else mem_start
            )
            cpu_end = process.cpu_percent() if process is not None else 0.0

            if is_profile_enabled():
                logger.debug(
                    f"[PROFILE] {func.__qualname__}: {duration:.2f}ms | Mem: {mem_end - mem_start:+.2f}MB | CPU: {cpu_end:.1f}%"
                )
            if is_debug_enabled():
                logger.debug(f"[SENTINEL] Exit {func.__qualname__}")

    return cast(Callable[P, R], wrapper)
