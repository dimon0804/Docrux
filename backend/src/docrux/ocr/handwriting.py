"""Чтение рукописных значений.

Tesseract обучен на печатном тексте и почерк не разбирает. Для полей,
заполненных от руки, используется открытая модель TrOCR, дообученная на
русском почерке. Она работает на процессоре через ONNX Runtime и читает по
одной строке: сервис вырезает область значения рядом с меткой и передаёт её
модели.

Модель необязательна. Если её файлов нет, сервис работает как раньше и
рукописные поля помечает как «не найдено».
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

import cv2
import numpy as np

MAX_TOKENS = 48
INPUT_SIZE = 384


class HandwritingReader:
    name = "trocr-ru"

    def __init__(self, directory: Path):
        import onnxruntime as ort
        from tokenizers import Tokenizer

        options = ort.SessionOptions()
        options.intra_op_num_threads = max(1, min(4, os.cpu_count() or 1))
        options.log_severity_level = 3
        providers = ["CPUExecutionProvider"]
        self.encoder = ort.InferenceSession(
            str(_pick(directory, "encoder_model")), options, providers=providers
        )
        self.decoder = ort.InferenceSession(
            str(_pick(directory, "decoder_model")), options, providers=providers
        )
        self.tokenizer = Tokenizer.from_file(str(directory / "tokenizer.json"))

        config = _read_json(directory / "generation_config.json")
        nested = _read_json(directory / "config.json").get("decoder", {})
        self.start = int(
            config.get("decoder_start_token_id", nested.get("decoder_start_token_id", 2))
        )
        self.eos = int(config.get("eos_token_id", nested.get("eos_token_id", 2)))
        self.decoder_inputs = {item.name for item in self.decoder.get_inputs()}

    @classmethod
    def load(cls, directory: str | os.PathLike[str] | None) -> HandwritingReader | None:
        """Возвращает читалку, если модель лежит в папке и зависимости установлены."""
        if not directory:
            return None
        path = Path(directory)
        if not (path / "tokenizer.json").exists():
            return None
        try:
            return cls(path)
        except (ImportError, FileNotFoundError):
            return None

    def read(self, crop: np.ndarray) -> tuple[str, float]:
        """Распознаёт одну рукописную строку. Возвращает текст и уверенность от 0 до 1."""
        pixels = _preprocess(crop)
        hidden = self.encoder.run(None, {self.encoder.get_inputs()[0].name: pixels})[0]

        tokens = [self.start]
        log_probability = 0.0
        for _ in range(MAX_TOKENS):
            feed = {"input_ids": np.asarray([tokens], dtype=np.int64)}
            if "encoder_hidden_states" in self.decoder_inputs:
                feed["encoder_hidden_states"] = hidden
            logits = self.decoder.run(None, feed)[0][0, -1]
            logits = logits - logits.max()
            probabilities = np.exp(logits) / np.exp(logits).sum()
            token = int(probabilities.argmax())
            if token == self.eos:
                break
            log_probability += math.log(max(float(probabilities[token]), 1e-9))
            tokens.append(token)

        text = self.tokenizer.decode(tokens[1:], skip_special_tokens=True).strip()
        steps = max(1, len(tokens) - 1)
        return text, math.exp(log_probability / steps)


def _pick(directory: Path, stem: str) -> Path:
    """Берёт сжатый вариант модели, если он есть, иначе полный."""
    for name in (f"{stem}_quantized.onnx", f"{stem}_int8.onnx", f"{stem}.onnx"):
        for base in (directory, directory / "onnx"):
            if (base / name).exists():
                return base / name
    raise FileNotFoundError(stem)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _preprocess(crop: np.ndarray) -> np.ndarray:
    """Картинка строки в формате, которого ждёт энкодер: 384x384, значения от -1 до 1."""
    rgb = (
        cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        if crop.ndim == 3
        else cv2.cvtColor(crop, cv2.COLOR_GRAY2RGB)
    )
    resized = cv2.resize(rgb, (INPUT_SIZE, INPUT_SIZE), interpolation=cv2.INTER_LINEAR)
    scaled = (resized.astype(np.float32) / 255.0 - 0.5) / 0.5
    return scaled.transpose(2, 0, 1)[None]
