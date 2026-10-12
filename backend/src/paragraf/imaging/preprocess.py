"""Подготовка снимка к распознаванию.

Чистый скан проходит почти без изменений. Фото с наклоном, тенью, бликом или
малым разрешением выравнивается и осветляется, чтобы OCR видел ровный текст
на светлом фоне.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

TARGET_WIDTH = 1700
MIN_WIDTH_FOR_UPSCALE = 1400
MAX_SIDE = 3000


@dataclass
class Prepared:
    color: np.ndarray
    """Выровненный снимок в BGR: его видит пользователь, по нему ищутся подпись и печать."""
    gray: np.ndarray
    """Осветлённое серое изображение для OCR."""
    quality: dict[str, float | str | bool] = field(default_factory=dict)


def prepare(image: np.ndarray) -> Prepared:
    quality: dict[str, float | str | bool] = {
        "source_width": int(image.shape[1]),
        "source_height": int(image.shape[0]),
    }
    image = _limit_size(image)

    cropped = _crop_page(image)
    quality["page_cropped"] = cropped is not None
    if cropped is not None:
        image = cropped

    angle = estimate_skew(image)
    quality["skew_degrees"] = round(angle, 2)
    if abs(angle) >= 0.3:
        image = rotate(image, angle)

    scale = 1.0
    if image.shape[1] < MIN_WIDTH_FOR_UPSCALE:
        scale = TARGET_WIDTH / image.shape[1]
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    quality["upscale"] = round(scale, 2)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    quality["sharpness"] = round(float(cv2.Laplacian(gray, cv2.CV_64F).var()), 1)

    uneven = _illumination_spread(gray)
    quality["uneven_light"] = round(uneven, 3)
    flattened = uneven > 0.06
    quality["light_corrected"] = flattened
    if flattened:
        gray = flatten_light(gray)
        image = _flatten_color(image)
    return Prepared(color=image, gray=gray, quality=quality)


def _limit_size(image: np.ndarray) -> np.ndarray:
    longest = max(image.shape[:2])
    if longest <= MAX_SIDE:
        return image
    scale = MAX_SIDE / longest
    return cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)


def estimate_skew(image: np.ndarray, limit: float = 40.0) -> float:
    """Угол наклона текста в градусах.

    Перебираем углы и смотрим, при каком строки текста дают самый «полосатый»
    профиль по горизонтали: у ровных строк между ними чистые промежутки.
    """
    gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    scale = 700 / max(gray.shape)
    small = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    background = cv2.morphologyEx(small, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    ink = cv2.subtract(background, small)
    _, ink = cv2.threshold(ink, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if cv2.countNonZero(ink) < 50:
        return 0.0

    def score(angle: float) -> float:
        rows = _rotate_bound(ink, angle).sum(axis=1, dtype=np.float64)
        return float(np.sum((rows[1:] - rows[:-1]) ** 2))

    best = max(np.arange(-limit, limit + 0.1, 1.0), key=score)
    best = max(np.arange(best - 1, best + 1.01, 0.2), key=score)
    best = max(np.arange(best - 0.2, best + 0.21, 0.05), key=score)
    return float(best) if abs(best) >= 0.05 else 0.0


def _rotate_bound(image: np.ndarray, angle: float, border: int | tuple = 0) -> np.ndarray:
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
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=border,
    )


def rotate(image: np.ndarray, angle: float) -> np.ndarray:
    """Поворачивает снимок, заполняя углы цветом фона страницы."""
    edge = np.concatenate([image[0], image[-1], image[:, 0], image[:, -1]])
    fill = tuple(int(v) for v in np.median(edge.reshape(-1, image.shape[2]), axis=0))
    return _rotate_bound(image, angle, border=fill)


def _illumination_spread(gray: np.ndarray) -> float:
    """Насколько неравномерно освещён фон: 0 у скана, заметно больше у фото с тенью."""
    small = cv2.resize(gray, (64, 64), interpolation=cv2.INTER_AREA)
    background = cv2.morphologyEx(small, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    background = cv2.GaussianBlur(background, (0, 0), 3).astype(np.float32) / 255
    return float(np.percentile(background, 95) - np.percentile(background, 5))


def flatten_light(gray: np.ndarray) -> np.ndarray:
    """Убирает тени и засветы: делит снимок на оценку фона."""
    kernel = max(31, (min(gray.shape) // 20) | 1)
    background = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    background = cv2.medianBlur(background, min(kernel, 255) | 1)
    flat = cv2.divide(gray, background, scale=255)
    return cv2.normalize(flat, None, 0, 255, cv2.NORM_MINMAX)


def _flatten_color(image: np.ndarray) -> np.ndarray:
    channels = [flatten_light(channel) for channel in cv2.split(image)]
    return cv2.merge(channels)


def _crop_page(image: np.ndarray) -> np.ndarray | None:
    """Вырезает лист, если он сфотографирован на тёмном или пёстром фоне.

    Возвращает None, когда лист и так занимает весь кадр или контур найти не удалось.
    """
    height, width = image.shape[:2]
    scale = 600 / max(height, width)
    small = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    gray = cv2.GaussianBlur(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    contour = max(contours, key=cv2.contourArea)
    share = cv2.contourArea(contour) / (small.shape[0] * small.shape[1])
    if not 0.25 <= share <= 0.92:
        return None
    quad = cv2.approxPolyDP(contour, 0.02 * cv2.arcLength(contour, True), True)
    if len(quad) != 4 or not cv2.isContourConvex(quad):
        return None
    corners = _order_corners(quad.reshape(4, 2).astype(np.float32) / scale)
    top = np.linalg.norm(corners[1] - corners[0])
    bottom = np.linalg.norm(corners[2] - corners[3])
    left = np.linalg.norm(corners[3] - corners[0])
    right = np.linalg.norm(corners[2] - corners[1])
    out_w, out_h = int(max(top, bottom)), int(max(left, right))
    if out_w < 300 or out_h < 300:
        return None
    target = np.array([[0, 0], [out_w - 1, 0], [out_w - 1, out_h - 1], [0, out_h - 1]], np.float32)
    matrix = cv2.getPerspectiveTransform(corners, target)
    return cv2.warpPerspective(
        image, matrix, (out_w, out_h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )


def _order_corners(points: np.ndarray) -> np.ndarray:
    """Углы в порядке: левый верхний, правый верхний, правый нижний, левый нижний."""
    total = points.sum(axis=1)
    diff = np.diff(points, axis=1).ravel()
    return np.array(
        [
            points[np.argmin(total)],
            points[np.argmin(diff)],
            points[np.argmax(total)],
            points[np.argmax(diff)],
        ],
        dtype=np.float32,
    )
