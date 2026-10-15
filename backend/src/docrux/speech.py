"""Вопрос голосом: распознавание речи небольшой открытой моделью Vosk.

Модель работает на процессоре внутри сервиса, звук никуда не отправляется.
Браузер сам приводит запись к WAV 16 кГц, моно, 16 бит, поэтому здесь не
нужен ни ffmpeg, ни разбор сжатых форматов.
"""

from __future__ import annotations

import io
import json
import threading
import wave
from pathlib import Path

SAMPLE_RATE = 16000
MAX_SECONDS = 20
MAX_BYTES = SAMPLE_RATE * 2 * MAX_SECONDS + 1024


class SpeechError(ValueError):
    """Запись нельзя распознать; текст ошибки показывается посетителю."""


class SpeechRecognizer:
    def __init__(self, model_dir: Path):
        from vosk import Model, SetLogLevel

        SetLogLevel(-1)
        self._model = Model(str(model_dir))
        self._lock = threading.Lock()

    @classmethod
    def load(cls, model_dir: Path | None) -> SpeechRecognizer | None:
        """Модель необязательная: нет папки или пакета vosk — голос просто выключен."""
        if model_dir is None or not (model_dir / "am").is_dir():
            return None
        try:
            return cls(model_dir)
        except ImportError:
            return None

    def transcribe(self, data: bytes) -> str:
        if len(data) > MAX_BYTES:
            raise SpeechError(f"Запись длиннее {MAX_SECONDS} секунд.")
        try:
            with wave.open(io.BytesIO(data)) as audio:
                if (
                    audio.getnchannels() != 1
                    or audio.getsampwidth() != 2
                    or audio.getframerate() != SAMPLE_RATE
                ):
                    raise SpeechError("Нужна запись WAV: 16 кГц, моно, 16 бит.")
                frames = audio.readframes(audio.getnframes())
        except (wave.Error, EOFError) as exc:
            raise SpeechError("Не удалось прочитать запись.") from exc
        from vosk import KaldiRecognizer

        # Модель общая, распознаватель свой на каждую запись.
        with self._lock:
            recognizer = KaldiRecognizer(self._model, SAMPLE_RATE)
        recognizer.AcceptWaveform(frames)
        text = json.loads(recognizer.FinalResult()).get("text", "")
        return text.strip()
