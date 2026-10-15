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
BLURRY_SHARPNESS = 40.0
"""Ниже этой дисперсии лапласиана снимок считается смазанным (чёткие сканы дают от 230)."""


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
    # Смазанный снимок: нерезкое маскирование возвращает буквам края. На смазанных
    # тестовых снимках это возвращает потерянные номера справок, чёткие снимки не трогаем.
    blurry = quality["sharpness"] < BLURRY_SHARPNESS
    quality["sharpened"] = blurry
    if blurry:
        soft = cv2.GaussianBlur(gray, (0, 0), 2.0)
        gray = cv2.addWeighted(gray, 2.0, soft, -1.0, 0)
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
    """Вырезает лист, если он сфотографирован на столе, и исправляет перспективу.

    Контур листа ищется несколькими способами: по яркости, по цветности и по
    границам. Подходит только тот, внутри которого лежит весь текст, а форма
    похожа на лист бумаги. Если такого нет, возвращается None и снимок не
    обрезается: ошибочная обрезка вреднее, чем её отсутствие.
    """
    height, width = image.shape[:2]
    scale = 640 / max(height, width)
    small = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    gray = cv2.GaussianBlur(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    ink = _relative_ink(gray)
    if cv2.countNonZero(ink) < 40:
        return None

    best: tuple[float, np.ndarray] | None = None
    for mask in _sheet_masks(small, gray):
        quad = _largest_quad(mask)
        if quad is None or not _is_sheet(ink, quad, gray.shape):
            continue
        area = cv2.contourArea(quad)
        if best is None or area > best[0]:
            best = (area, quad)
    if best is None:
        return None

    corners = _order_corners(best[1].reshape(4, 2).astype(np.float32) / scale)
    top = np.linalg.norm(corners[1] - corners[0])
    bottom = np.linalg.norm(corners[2] - corners[3])
    left = np.linalg.norm(corners[3] - corners[0])
    right = np.linalg.norm(corners[2] - corners[1])
    out_w, out_h = int(max(top, bottom)), int(max(left, right))
    if out_w < 300 or out_h < 300:
        return None
    target = np.array([[0, 0], [out_w - 1, 0], [out_w - 1, out_h - 1], [0, out_h - 1]], np.float32)
    matrix = cv2.getPerspectiveTransform(corners, target)
    warped = cv2.warpPerspective(
        image, matrix, (out_w, out_h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )
    # По краю почти всегда остаётся полоска стола: срезаем её.
    trim_x, trim_y = max(2, int(out_w * 0.008)), max(2, int(out_h * 0.008))
    return warped[trim_y:-trim_y, trim_x:-trim_x]


def _relative_ink(gray: np.ndarray) -> np.ndarray:
    """Маска текста по относительному контрасту: в тени он падает, а отношение остаётся."""
    background = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    background = np.maximum(background, 1).astype(np.float32)
    ratio = 1.0 - gray.astype(np.float32) / background
    return (ratio > 0.22).astype(np.uint8) * 255


def _sheet_masks(small: np.ndarray, gray: np.ndarray) -> list[np.ndarray]:
    """Кандидаты в маску листа, полученные разными способами."""
    close = np.ones((21, 21), np.uint8)
    masks = []

    _, bright = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    masks.append(cv2.morphologyEx(bright, cv2.MORPH_CLOSE, close))

    # Бумага почти бесцветна, стол обычно имеет оттенок. Цветность мало зависит от тени.
    lab = cv2.cvtColor(small, cv2.COLOR_BGR2LAB).astype(np.float32)
    chroma = cv2.magnitude(lab[..., 1] - 128, lab[..., 2] - 128)
    chroma = cv2.GaussianBlur(np.clip(chroma * 4, 0, 255).astype(np.uint8), (5, 5), 0)
    threshold, neutral = cv2.threshold(chroma, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    if threshold >= 12:
        masks.append(cv2.morphologyEx(neutral, cv2.MORPH_CLOSE, close))

    # Границы листа: замкнутая область внутри контура перепадов яркости.
    edges = cv2.Canny(gray, 30, 90)
    edges = cv2.dilate(edges, np.ones((5, 5), np.uint8))
    filled = np.zeros_like(gray)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        cv2.drawContours(filled, [max(contours, key=cv2.contourArea)], -1, 255, cv2.FILLED)
        masks.append(filled)
    return masks


def _largest_quad(mask: np.ndarray) -> np.ndarray | None:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    contour = cv2.convexHull(max(contours, key=cv2.contourArea))
    share = cv2.contourArea(contour) / (mask.shape[0] * mask.shape[1])
    if not 0.2 <= share <= 0.93:
        return None
    perimeter = cv2.arcLength(contour, True)
    for tolerance in (0.02, 0.03, 0.05):
        quad = cv2.approxPolyDP(contour, tolerance * perimeter, True)
        if len(quad) == 4 and cv2.isContourConvex(quad):
            return quad
    return None


def _is_sheet(ink: np.ndarray, quad: np.ndarray, shape: tuple[int, ...]) -> bool:
    """Проверяет, что контур действительно лист: весь текст внутри, форма как у бумаги."""
    points = quad.reshape(4, 2).astype(np.float32)
    ordered = _order_corners(points)
    sides = [float(np.linalg.norm(ordered[(i + 1) % 4] - ordered[i])) for i in range(4)]
    if min(sides) < 0.25 * max(shape):
        return False
    horizontal, vertical = (sides[0] + sides[2]) / 2, (sides[1] + sides[3]) / 2
    ratio = min(horizontal, vertical) / max(horizontal, vertical)
    if not 0.55 <= ratio <= 0.92:
        return False
    if min(sides[0], sides[2]) / max(sides[0], sides[2]) < 0.75:
        return False
    if min(sides[1], sides[3]) / max(sides[1], sides[3]) < 0.75:
        return False

    inside = np.zeros(shape[:2], np.uint8)
    cv2.fillConvexPoly(inside, ordered.astype(np.int32), 255)
    total = cv2.countNonZero(ink)
    outside = cv2.countNonZero(cv2.bitwise_and(ink, cv2.bitwise_not(inside)))
    return total > 0 and outside / total <= 0.06


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
