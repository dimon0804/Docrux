"""Портит чистые снимки так, как это делает телефон: наклон, тень, блик, низкое разрешение.

Из набора в формате организаторов делает такой же набор с испорченными
изображениями, чтобы измерить, насколько сервис устойчив к плохим фото.

    python tools/degrade.py data/open data/open-tilt --mode tilt
    python tools/degrade.py data/open data/open-photo --mode photo
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
from pathlib import Path

import cv2
import numpy as np

MODES = ["tilt", "shadow", "glare", "lowres", "jpeg", "blur", "photo"]


def tilt(image: np.ndarray, rng: random.Random, limit: float = 30.0) -> np.ndarray:
    """Поворот на случайный угол до 30 градусов с серым «столом» вокруг листа."""
    angle = rng.uniform(-limit, limit)
    if abs(angle) < 4:
        angle = 4 if angle >= 0 else -4
    height, width = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1.0)
    cos, sin = abs(matrix[0, 0]), abs(matrix[0, 1])
    new_w, new_h = int(height * sin + width * cos), int(height * cos + width * sin)
    matrix[0, 2] += new_w / 2 - width / 2
    matrix[1, 2] += new_h / 2 - height / 2
    return cv2.warpAffine(
        image,
        matrix,
        (new_w, new_h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(238, 238, 238),
    )


def shadow(image: np.ndarray, rng: random.Random) -> np.ndarray:
    """Косая тень от руки или телефона: половина листа темнее."""
    height, width = image.shape[:2]
    ys, xs = np.mgrid[0:height, 0:width].astype(np.float32)
    angle = rng.uniform(0, np.pi)
    offset = rng.uniform(0.35, 0.65)
    ramp = (xs / width * np.cos(angle) + ys / height * np.sin(angle)) - offset
    mask = 1 / (1 + np.exp(-ramp * rng.uniform(10, 25)))
    strength = rng.uniform(0.35, 0.55)
    gain = 1 - strength * mask
    return np.clip(image.astype(np.float32) * gain[..., None], 0, 255).astype(np.uint8)


def glare(image: np.ndarray, rng: random.Random) -> np.ndarray:
    """Блик от лампы: светлое пятно, которое вымывает контраст."""
    height, width = image.shape[:2]
    ys, xs = np.mgrid[0:height, 0:width].astype(np.float32)
    cx, cy = rng.uniform(0.2, 0.8) * width, rng.uniform(0.15, 0.6) * height
    radius = rng.uniform(0.18, 0.3) * width
    spot = np.exp(-(((xs - cx) ** 2 + (ys - cy) ** 2) / (2 * radius**2)))
    strength = rng.uniform(0.55, 0.75)
    out = image.astype(np.float32)
    out = out + (255 - out) * (spot * strength)[..., None]
    return np.clip(out, 0, 255).astype(np.uint8)


def lowres(image: np.ndarray, rng: random.Random) -> np.ndarray:
    """Маленькое фото: ширина около 600 пикселей."""
    width = rng.randint(580, 680)
    scale = width / image.shape[1]
    return cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)


def jpeg(image: np.ndarray, rng: random.Random) -> np.ndarray:
    """Сильное сжатие, как после пересылки в мессенджере."""
    ok, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, rng.randint(22, 38)])
    return cv2.imdecode(buffer, cv2.IMREAD_COLOR) if ok else image


def blur(image: np.ndarray, rng: random.Random) -> np.ndarray:
    """Лёгкий смаз и шум матрицы."""
    out = cv2.GaussianBlur(image, (0, 0), rng.uniform(0.9, 1.4))
    noise = np.random.default_rng(rng.randrange(1 << 30)).normal(0, 5, out.shape)
    return np.clip(out.astype(np.float32) + noise, 0, 255).astype(np.uint8)


def photo(image: np.ndarray, rng: random.Random) -> np.ndarray:
    """Снимок телефоном: лист на столе, перспектива, наклон, тень, сжатие."""
    height, width = image.shape[:2]
    canvas_w, canvas_h = int(width * 1.25), int(height * 1.2)
    desk = np.full((canvas_h, canvas_w, 3), (72, 92, 118), np.uint8)
    grain = np.random.default_rng(rng.randrange(1 << 30)).normal(0, 9, desk.shape)
    desk = np.clip(desk.astype(np.float32) + grain, 0, 255).astype(np.uint8)

    margin_x, margin_y = (canvas_w - width) / 2, (canvas_h - height) / 2
    jitter = lambda: rng.uniform(-0.035, 0.035) * width  # noqa: E731
    source = np.float32([[0, 0], [width, 0], [width, height], [0, height]])
    target = np.float32(
        [
            [margin_x + jitter(), margin_y + jitter()],
            [margin_x + width + jitter(), margin_y + jitter()],
            [margin_x + width + jitter(), margin_y + height + jitter()],
            [margin_x + jitter(), margin_y + height + jitter()],
        ]
    )
    matrix = cv2.getPerspectiveTransform(source, target)
    warped = cv2.warpPerspective(image, matrix, (canvas_w, canvas_h), flags=cv2.INTER_CUBIC)
    mask = cv2.warpPerspective(
        np.full((height, width), 255, np.uint8), matrix, (canvas_w, canvas_h)
    )
    out = np.where(mask[..., None] > 0, warped, desk)

    angle = rng.uniform(-12, 12)
    rotation = cv2.getRotationMatrix2D((canvas_w / 2, canvas_h / 2), angle, 1.0)
    out = cv2.warpAffine(
        out,
        rotation,
        (canvas_w, canvas_h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
    out = shadow(out, rng)
    scale = rng.uniform(0.8, 1.0)
    out = cv2.resize(out, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    ok, buffer = cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, rng.randint(55, 75)])
    return cv2.imdecode(buffer, cv2.IMREAD_COLOR) if ok else out


TRANSFORMS = {
    "tilt": tilt,
    "shadow": shadow,
    "glare": glare,
    "lowres": lowres,
    "jpeg": jpeg,
    "blur": blur,
    "photo": photo,
}


def degrade(source: Path, target: Path, mode: str, seed: int) -> int:
    rng = random.Random(seed)
    (target / "documents").mkdir(parents=True, exist_ok=True)
    for name in ["questions.json", "reference_results.json"]:
        if (source / name).exists():
            shutil.copyfile(source / name, target / name)
    manifest = json.loads((source / "documents.json").read_text(encoding="utf-8"))
    out_manifest = []
    for entry in manifest:
        image = cv2.imdecode(
            np.fromfile(str(source / entry["image"]), dtype=np.uint8), cv2.IMREAD_COLOR
        )
        result = TRANSFORMS[mode](image, rng)
        relative = f"documents/{entry['document_id']}.jpg"
        quality = 92 if mode != "jpeg" else 95
        ok, buffer = cv2.imencode(".jpg", result, [cv2.IMWRITE_JPEG_QUALITY, quality])
        if not ok:
            raise RuntimeError(f"не удалось сохранить {relative}")
        buffer.tofile(str(target / relative))
        out_manifest.append(
            {
                "document_id": entry["document_id"],
                "document_type": entry["document_type"],
                "image": relative,
            }
        )
    (target / "documents.json").write_text(
        json.dumps(out_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return len(out_manifest)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--seed", type=int, default=11)
    arguments = parser.parse_args()
    count = degrade(arguments.source, arguments.target, arguments.mode, arguments.seed)
    print(f"{arguments.mode}: {count} снимков в {arguments.target}")
