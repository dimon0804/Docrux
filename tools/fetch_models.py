"""Скачивает необязательные модели в папку models/.

Без них сервис работает полностью: читает печатные документы и отвечает по
Положению. Модели добавляют две возможности:

  handwriting  чтение полей, заполненных от руки (TrOCR, около 1,5 ГБ)
  llm          ответы на вопросы, заданные своими словами (Vikhr-Qwen 1.5B, около 1,1 ГБ)

    python tools/fetch_models.py handwriting llm

Закачку можно прервать и запустить снова: она продолжится с того же места.
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "models"
TROCR = "https://huggingface.co/Mievst/trocr-base-handwritten-ru-ONNX/resolve/main"
VIKHR = "https://huggingface.co/Vikhrmodels/Vikhr-Qwen-2.5-1.5B-Instruct-GGUF/resolve/main"

MODELS: dict[str, list[tuple[str, str]]] = {
    "handwriting": [
        (f"{TROCR}/{name}", f"trocr-ru/{name}")
        for name in (
            "config.json",
            "generation_config.json",
            "preprocessor_config.json",
            "tokenizer.json",
            "tokenizer_config.json",
            "special_tokens_map.json",
            "vocab.json",
            "merges.txt",
        )
    ]
    + [
        (f"{TROCR}/onnx/encoder_model.onnx", "trocr-ru/encoder_model.onnx"),
        (f"{TROCR}/onnx/decoder_model.onnx", "trocr-ru/decoder_model.onnx"),
    ],
    "llm": [(f"{VIKHR}/Vikhr-Qwen-2.5-1.5b-Instruct-Q5_K_M.gguf", "llm/model.gguf")],
}


def remote_size(url: str) -> int:
    request = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
        return int(response.headers.get("Content-Length", 0))


def fetch(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    total = remote_size(url)
    done = target.stat().st_size if target.exists() else 0
    if total and done >= total:
        print(f"  уже есть: {target.name}")
        return
    request = urllib.request.Request(url, headers={"Range": f"bytes={done}-"} if done else {})
    with urllib.request.urlopen(request, timeout=120) as response, target.open("ab") as out:  # noqa: S310
        while chunk := response.read(1 << 20):
            out.write(chunk)
            done += len(chunk)
            if total:
                print(f"\r  {target.name}: {done * 100 // total}%", end="", flush=True)
    print()


def main(names: list[str]) -> int:
    unknown = [name for name in names if name not in MODELS]
    if not names or unknown:
        print(__doc__)
        return 1
    for name in names:
        print(f"{name}:")
        for url, relative in MODELS[name]:
            for attempt in range(1, 21):
                try:
                    fetch(url, ROOT / relative)
                    break
                except OSError as error:
                    print(f"\n  обрыв связи ({error}), попытка {attempt} из 20")
            else:
                print(f"  не удалось скачать {relative}")
                return 2
    print(f"Готово. Модели лежат в {ROOT}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
