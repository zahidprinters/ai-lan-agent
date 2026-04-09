import pytest
from pathlib import Path
from tools.perception.vision import capture_screen_text


def test_capture_screen_text():
    # Clear any existing screenshot
    screenshot_path = Path("temp/screen.png")
    if screenshot_path.exists():
        screenshot_path.unlink()

    result = capture_screen_text()

    # Check if a screenshot was actually taken
    assert screenshot_path.exists(), "Screenshot file should be created"

    # Result should be a string (even if it's an error message about Tesseract)
    assert isinstance(result, str)

    if "Vision perception error" in result and "tesseract" in result.lower():
        pytest.skip("Tesseract-OCR not installed on this system, but screenshot capture worked.")

    # If it didn't fail due to tesseract, it might be empty or contain text
    print(f"OCR Result: {result}")
