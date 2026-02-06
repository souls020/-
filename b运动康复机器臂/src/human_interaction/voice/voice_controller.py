#!/usr/bin/env python3
"""
Voice Controller
Speech recognition and voice command handling for rehabilitation robot
"""

import threading
import time
import numpy as np
from typing import Dict, List, Callable, Optional
from dataclasses import dataclass
from enum import Enum
import logging


class VoiceEngine(Enum):
    """Supported voice recognition engines."""
    SPEECH_RECOGNITION = "speech_recognition"
    WHISPER = "whisper"
    VOSK = "vosk"


@dataclass
class VoiceCommand:
    """Parsed voice command."""
    command: str
    action: str
    parameters: Dict
    confidence: float


class VoiceController:
    """
    Voice control interface for rehabilitation robot.
    Provides speech recognition and command parsing.
    """

    def __init__(self, engine: VoiceEngine = VoiceEngine.SPEECH_RECOGNITION):
        """
        Initialize voice controller.

        Args:
            engine: Voice recognition engine to use
        """
        self.engine = engine
        self.logger = logging.getLogger(__name__)

        # State
        self.is_listening = False
        self.is_paused = False
        self.command_callback: Optional[Callable] = None

        # Command mappings
        self.command_mappings = self._build_command_mappings()

        # Recognition setup
        self._setup_recognition()

        # Commands
        self.available_commands = [
            "start training",
            "stop training",
            "pause training",
            "resume training",
            "increase speed",
            "decrease speed",
            "increase range",
            "decrease range",
            "more assistance",
            "less assistance",
            "emergency stop",
            "reset emergency",
            "next exercise",
            "previous exercise",
            "status report"
        ]

        self.logger.info("Voice Controller initialized")

    def _setup_recognition(self):
        """Setup speech recognition engine."""
        try:
            if self.engine == VoiceEngine.SPEECH_RECOGNITION:
                import speech_recognition as sr
                self.recognizer = sr.Recognizer()
                self.microphone = sr.Microphone()
                # Adjust for ambient noise
                with self.microphone as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            elif self.engine == VoiceEngine.WHISPER:
                import whisper
                self.whisper_model = whisper.load_model("base")
            elif self.engine == VoiceEngine.VOSK:
                from vosk import Model, KaldiRecognizer
                self.vosk_model = Model(lang="en")
                self.vosk_recognizer = KaldiRecognizer(self.vosk_model, 16000)

        except ImportError as e:
            self.logger.warning(f"Voice engine not available: {e}")
            self.engine = None

    def _build_command_mappings(self) -> Dict:
        """Build command word mappings."""
        return {
            # Training control
            "start": "start_training",
            "begin": "start_training",
            "go": "start_training",
            "stop": "stop_training",
            "halt": "stop_training",
            "end": "stop_training",
            "pause": "pause_training",
            "hold": "pause_training",
            "resume": "resume_training",
            "continue": "resume_training",

            # Parameter control
            "faster": "increase_speed",
            "slow down": "decrease_speed",
            "slower": "decrease_speed",
            "wider": "increase_range",
            "bigger": "increase_range",
            "narrower": "decrease_range",
            "smaller": "decrease_range",
            "more help": "increase_assistance",
            "more assistance": "increase_assistance",
            "less help": "decrease_assistance",
            "less assistance": "decrease_assistance",

            # Emergency
            "emergency": "emergency_stop",
            "stop now": "emergency_stop",
            "danger": "emergency_stop",
            "reset": "reset_emergency",
            "okay": "reset_emergency",
            "ok": "reset_emergency",

            # Navigation
            "next": "next_exercise",
            "previous": "previous_exercise",
            "back": "previous_exercise",

            # Status
            "status": "status_report",
            "report": "status_report",
            "how are you": "status_report"
        }

    def start_listening(self):
        """Start listening for voice commands."""
        if self.is_listening:
            return

        self.is_listening = True
        self.is_paused = False

        # Start recognition thread
        if self.engine == VoiceEngine.SPEECH_RECOGNITION:
            self.listen_thread = threading.Thread(target=self._listen_sr, daemon=True)
            self.listen_thread.start()
        elif self.engine == VoiceEngine.WHISPER:
            self.listen_thread = threading.Thread(target=self._listen_whisper, daemon=True)
            self.listen_thread.start()
        elif self.engine == VoiceEngine.VOSK:
            self.listen_thread = threading.Thread(target=self._listen_vosk, daemon=True)
            self.listen_thread.start()

        self.logger.info("Voice listening started")

    def stop_listening(self):
        """Stop listening for voice commands."""
        self.is_listening = False
        self.is_paused = False
        # Wait for listening thread to terminate
        if hasattr(self, 'listen_thread') and self.listen_thread.is_alive():
            self.listen_thread.join(timeout=2.0)
        self.logger.info("Voice listening stopped")

    def pause_listening(self):
        """Pause listening without stopping."""
        self.is_paused = True

    def resume_listening(self):
        """Resume paused listening."""
        self.is_paused = False

    def _listen_sr(self):
        """Listen using SpeechRecognition library."""
        import speech_recognition as sr

        while self.is_listening:
            if self.is_paused:
                time.sleep(0.1)
                continue

            try:
                with self.microphone as source:
                    audio = self.recognizer.listen(source, timeout=1.0, phrase_time_limit=3.0)

                text = self.recognizer.recognize_google(audio)
                self._process_command(text)

            except sr.WaitTimeoutError:
                continue
            except sr.UnknownValueError:
                continue
            except Exception as e:
                self.logger.error(f"Recognition error: {e}")

    def _listen_whisper(self):
        """Listen using OpenAI Whisper."""
        import pyaudio
        import wave

        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True)

        while self.is_listening:
            if self.is_paused:
                time.sleep(0.1)
                continue

            try:
                # Record audio chunk
                frames = []
                for _ in range(0, int(16000 / 1024 * 3)):  # 3 seconds
                    data = stream.read(1024)
                    frames.append(data)

                # Transcribe
                audio_data = wave.open('temp_audio.wav', 'wb')
                audio_data.setnchannels(1)
                audio_data.setsampwidth(p.get_sample_size(pyaudio.paInt16))
                audio_data.setframerate(16000)
                audio_data.writeframes(b''.join(frames))
                audio_data.close()

                result = self.whisper_model.transcribe("temp_audio.wav")
                if result["text"]:
                    self._process_command(result["text"])

            except Exception as e:
                self.logger.error(f"Whisper error: {e}")

        stream.stop_stream()
        stream.close()
        p.terminate()

    def _listen_vosk(self):
        """Listen using Vosk."""
        import pyaudio

        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True,
                       frames_per_buffer=8000)

        while self.is_listening:
            if self.is_paused:
                time.sleep(0.1)
                continue

            try:
                data = stream.read(4000, exception_on_overflow=False)

                if self.vosk_recognizer.AcceptWaveform(data):
                    result = json.loads(self.vosk_recognizer.FinalResult())
                    if result.get("text"):
                        self._process_command(result["text"])

            except Exception as e:
                self.logger.error(f"Vosk error: {e}")

        stream.stop_stream()
        stream.close()
        p.terminate()

    def _process_command(self, text: str):
        """
        Process recognized text and extract command.

        Args:
            text: Recognized speech text
        """
        text_lower = text.lower().strip()

        # Find matching command
        best_match = None
        best_score = 0

        for cmd, action in self.command_mappings.items():
            if cmd in text_lower:
                score = len(cmd) / len(text_lower)  # Longer matches score higher
                if score > best_score:
                    best_score = score
                    best_match = VoiceCommand(
                        command=text,
                        action=action,
                        parameters=self._extract_parameters(text_lower),
                        confidence=min(score + 0.3, 0.95)
                    )

        if best_match:
            self.logger.info(f"Voice command: {text} -> {best_match.action}")
            if self.command_callback:
                self.command_callback(best_match)
        else:
            self.logger.debug(f"Unrecognized command: {text}")

    def _extract_parameters(self, text: str) -> Dict:
        """Extract numerical parameters from command."""
        params = {}

        # Extract numbers
        import re
        numbers = re.findall(r'\d+(?:\.\d+)?', text)
        if numbers:
            params['values'] = [float(n) for n in numbers]

        # Extract percentages
        if '%' in text:
            percents = re.findall(r'(\d+)%', text)
            params['percentages'] = [int(p) for p in percents]

        return params

    def set_command_callback(self, callback: Callable[[VoiceCommand], None]):
        """
        Set callback for processed voice commands.

        Args:
            callback: Function to call with parsed commands
        """
        self.command_callback = callback

    def get_available_commands(self) -> List[str]:
        """Get list of available voice commands."""
        return self.available_commands

    def add_custom_command(self, phrase: str, action: str):
        """
        Add custom voice command.

        Args:
            phrase: Voice phrase to recognize
            action: Action to trigger
        """
        self.command_mappings[phrase.lower()] = action
        self.available_commands.append(phrase)

    def remove_custom_command(self, phrase: str):
        """Remove custom voice command."""
        phrase_lower = phrase.lower()
        if phrase_lower in self.command_mappings:
            del self.command_mappings[phrase_lower]
        if phrase in self.available_commands:
            self.available_commands.remove(phrase)


class MockVoiceController(VoiceController):
    """
    Mock voice controller for testing without audio hardware.
    """

    def __init__(self):
        super().__init__(engine=None)
        self.mock_commands = []
        self.mock_index = 0

    def add_mock_command(self, command: str, action: str):
        """Add mock command for testing."""
        self.mock_commands.append((command, action))

    def next_mock_command(self) -> Optional[VoiceCommand]:
        """Get next mock command."""
        if not self.mock_commands:
            return None

        cmd, action = self.mock_commands[self.mock_index % len(self.mock_commands)]
        self.mock_index += 1

        return VoiceCommand(
            command=cmd,
            action=action,
            parameters={},
            confidence=0.95
        )


def main():
    """Test voice controller."""
    import json

    # Create controller
    controller = VoiceController()

    # Set callback
    def on_command(cmd: VoiceCommand):
        print(f"Command: {cmd.command}")
        print(f"Action: {cmd.action}")
        print(f"Confidence: {cmd.confidence}")
        print()

    controller.set_command_callback(on_command)

    # Add mock commands for testing
    controller.add_mock_command("start training", "start_training")
    controller.add_mock_command("stop", "stop_training")
    controller.add_mock_command("emergency", "emergency_stop")

    # Test parsing
    test_inputs = [
        "start the training",
        "please stop",
        "this is an emergency"
    ]

    for text in test_inputs:
        controller._process_command(text)

    print("Voice controller test complete")


if __name__ == "__main__":
    main()
