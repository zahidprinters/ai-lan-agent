import pytest
from unittest.mock import MagicMock, patch
from tools.perception.audio.tts import Speaker


@patch("pyttsx3.init")
def test_speaker_initialization(mock_init):
    # Setup mock
    mock_engine = MagicMock()
    mock_init.return_value = mock_engine
    mock_voices = [MagicMock(id="voice1"), MagicMock(id="voice2")]
    mock_engine.getProperty.return_value = mock_voices

    # Initialize speaker
    speaker = Speaker()

    # Assertions
    mock_init.assert_called_once()
    mock_engine.setProperty.assert_any_call("rate", speaker.config.voice_rate)

    # Test _set_gender explicitly
    mock_engine.setProperty.reset_mock()
    speaker._set_gender("male")
    mock_engine.setProperty.assert_called_with("voice", "voice1")

    mock_engine.setProperty.reset_mock()
    speaker._set_gender("female")
    # In my implementation, it should select index 1 if available
    mock_engine.setProperty.assert_called_with("voice", "voice2")


@patch("pyttsx3.init")
def test_speaker_speak(mock_init):
    # Setup mock
    mock_engine = MagicMock()
    mock_init.return_value = mock_engine

    # Initialize speaker
    speaker = Speaker()

    # Test speak
    speaker.speak("Hello world")

    # Assertions
    mock_engine.say.assert_called_once_with("Hello world")
    mock_engine.runAndWait.assert_called_once()
