import pyttsx3
from training.config import load_config


class Speaker:
    def __init__(self):
        self.config = load_config()
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", self.config.voice_rate)
        self._set_gender(self.config.voice_gender)

    def _set_gender(self, gender: str):
        voices = self.engine.getProperty("voices")
        # Check if voices exist and handle accordingly
        if not voices:
            return
        # Usually 0 is male, 1 is female on Windows
        if gender == "male":
            self.engine.setProperty("voice", voices[0].id)
        else:
            self.engine.setProperty("voice", voices[min(1, len(voices) - 1)].id)

    def speak(self, text: str):
        self.engine.say(text)
        self.engine.runAndWait()
