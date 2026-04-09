"""Compatibility shim for legacy imports. Prefer tools/android modules."""

from tools.android.adb import launch_app, list_devices
from tools.android.input import swipe_screen, tap_screen
from tools.android.screen import capture_screenshot

__all__ = [
    "list_devices",
    "launch_app",
    "tap_screen",
    "swipe_screen",
    "capture_screenshot",
]
