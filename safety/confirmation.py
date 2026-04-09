"""User confirmation helper."""


def requires_confirmation(action_name: str) -> bool:
    return action_name in {
        "pc.type_text",
        "pc.open_app",
        "android.launch_app",
        "android.tap",
        "android.swipe",
        "android.capture_screenshot",
    }
