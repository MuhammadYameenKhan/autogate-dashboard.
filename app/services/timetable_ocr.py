"""
Timetable image OCR and schedule parsing.
Uses Tesseract (via pytesseract) with OpenCV preprocessing.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

DAY_ALIASES = {
    'mon': 'Monday', 'monday': 'Monday',
    'tue': 'Tuesday', 'tues': 'Tuesday', 'tuesday': 'Tuesday',
    'wed': 'Wednesday', 'wednesday': 'Wednesday',
    'thu': 'Thursday', 'thur': 'Thursday', 'thurs': 'Thursday', 'thursday': 'Thursday',
    'fri': 'Friday', 'friday': 'Friday',
    'sat': 'Saturday', 'saturday': 'Saturday',
    'sun': 'Sunday', 'sunday': 'Sunday',
}

TIME_RANGE_RE = re.compile(
    r'(\d{1,2})\s*[:.]\s*(\d{2})\s*'
    r'(?:-|–|—|\s+to\s+|\s+TO\s+)\s*'
    r'(\d{1,2})\s*[:.]\s*(\d{2})',
    re.IGNORECASE,
)
TIME_SINGLE_RE = re.compile(r'\b(\d{1,2})\s*[:.]\s*(\d{2})\b')
BUILDING_RE = re.compile(
    r'\b(?:block|blk|building|bldg|room|rm|hall)\s*[#:]?\s*([A-Za-z0-9]{1,4})\b',
    re.IGNORECASE,
)
BUILDING_ZONE_RE = re.compile(r'\b(?:zone|sector)\s*([A-D])\b', re.IGNORECASE)
STANDALONE_BUILDING_RE = re.compile(
    r'(?:^|[\s,|])([A-D])(?:\s*(?:block|bldg|building)|[\s,|]|$)',
    re.IGNORECASE,
)
DAY_TOKEN_RE = re.compile(
    r'\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|'
    r'Mon|Tue|Tues|Wed|Thu|Thur|Thurs|Fri|Sat|Sun)\b',
    re.IGNORECASE,
)


def _format_time(h: str, m: str) -> str:
    return f'{int(h):02d}:{m}'


def _normalize_day(token: str) -> Optional[str]:
    key = token.strip().lower().rstrip('.')
    return DAY_ALIASES.get(key)


def _extract_building(text: str) -> str:
    for pattern in (BUILDING_RE, BUILDING_ZONE_RE, STANDALONE_BUILDING_RE):
        match = pattern.search(text)
        if match:
            return match.group(1).upper()
    return ''


def _extract_time(text: str) -> str:
    range_match = TIME_RANGE_RE.search(text)
    if range_match:
        h1, m1, h2, m2 = range_match.groups()
        return f'{_format_time(h1, m1)} - {_format_time(h2, m2)}'

    times = TIME_SINGLE_RE.findall(text)
    if len(times) >= 2:
        return f'{_format_time(times[0][0], times[0][1])} - {_format_time(times[1][0], times[1][1])}'
    if len(times) == 1:
        return _format_time(times[0][0], times[0][1])
    return ''


def _extract_course(text: str, day: str, time_str: str, building: str) -> str:
    course = text
    course = TIME_RANGE_RE.sub(' ', course)
    course = TIME_SINGLE_RE.sub(' ', course)
    course = BUILDING_RE.sub(' ', course)
    course = BUILDING_ZONE_RE.sub(' ', course)
    course = DAY_TOKEN_RE.sub(' ', course)
    for token in (day, time_str, building):
        if token:
            course = re.sub(rf'\b{re.escape(token)}\b', ' ', course, flags=re.IGNORECASE)
    course = re.sub(r'\b(?:am|pm)\b', ' ', course, flags=re.IGNORECASE)
    course = re.sub(r'[^\w\s&/-]', ' ', course)
    course = re.sub(r'\s+', ' ', course).strip()
    if len(course) < 3:
        return ''
    return course[:120]


def parse_schedule_from_text(raw_text: str) -> list[dict]:
    """Parse OCR text into structured class entries."""
    if not raw_text or not raw_text.strip():
        return []

    classes: list[dict] = []
    seen: set[tuple] = set()
    current_day: Optional[str] = None

    lines = [re.sub(r'\s+', ' ', line).strip() for line in raw_text.splitlines()]
    lines = [line for line in lines if line]

    for line in lines:
        day_match = DAY_TOKEN_RE.search(line)
        if day_match:
            current_day = _normalize_day(day_match.group(1))

        day = current_day
        if not day:
            inline_day = DAY_TOKEN_RE.search(line)
            if inline_day:
                day = _normalize_day(inline_day.group(1))

        time_str = _extract_time(line)
        building = _extract_building(line)
        course = _extract_course(line, day or '', time_str, building)

        if not day or (not time_str and not course):
            continue

        entry = {
            'day': day,
            'time': time_str or 'TBA',
            'building': building or 'A',
            'course': course or 'Class',
        }
        key = (entry['day'], entry['time'], entry['building'], entry['course'])
        if key in seen:
            continue
        seen.add(key)
        classes.append(entry)

    if classes:
        return classes

    # Fallback: scan full text for day sections (grid-style timetables)
    for day_match in DAY_TOKEN_RE.finditer(raw_text):
        day = _normalize_day(day_match.group(1))
        if not day:
            continue
        start = day_match.end()
        next_day = DAY_TOKEN_RE.search(raw_text, start)
        chunk = raw_text[start: next_day.start() if next_day else len(raw_text)]
        for line in re.split(r'[\n;|]+', chunk):
            line = line.strip()
            if len(line) < 6:
                continue
            time_str = _extract_time(line)
            if not time_str:
                continue
            building = _extract_building(line)
            course = _extract_course(line, day, time_str, building)
            entry = {
                'day': day,
                'time': time_str,
                'building': building or 'A',
                'course': course or 'Class',
            }
            key = (entry['day'], entry['time'], entry['building'], entry['course'])
            if key not in seen:
                seen.add(key)
                classes.append(entry)

    return classes


def _preprocess_image(filepath: str):
    import cv2
    import numpy as np

    img = cv2.imread(filepath)
    if img is None:
        from PIL import Image
        pil_img = Image.open(filepath).convert('RGB')
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape
    scale = max(1.0, 1800 / max(width, height))
    if scale > 1.0:
        gray = cv2.resize(
            gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC
        )
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    _, thresh = cv2.threshold(
        denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    return thresh, gray


def ocr_image_to_text(filepath: str) -> str:
    """Run OCR on a timetable image and return raw text."""
    import pytesseract

    try:
        processed, gray = _preprocess_image(filepath)
    except Exception as exc:
        raise RuntimeError(f'Could not read image: {exc}') from exc

    configs = [
        '--oem 3 --psm 6',
        '--oem 3 --psm 4',
        '--oem 3 --psm 3',
    ]
    candidates: list[str] = []

    for config in configs:
        try:
            text = pytesseract.image_to_string(processed, config=config)
            if text.strip():
                candidates.append(text.strip())
        except Exception as exc:
            logger.warning('Tesseract failed with %s: %s', config, exc)

    try:
        raw_gray = pytesseract.image_to_string(gray, config='--oem 3 --psm 6')
        if raw_gray.strip():
            candidates.append(raw_gray.strip())
    except Exception:
        pass

    if not candidates:
        raise RuntimeError(
            'OCR produced no text. Install Tesseract: '
            'macOS: brew install tesseract | Ubuntu: apt install tesseract-ocr'
        )

    return max(candidates, key=len)


def extract_schedule_from_image(filepath: str) -> dict:
    """Full pipeline: OCR image → parse → {classes, rawText}."""
    raw_text = ocr_image_to_text(filepath)
    classes = parse_schedule_from_text(raw_text)
    return {'classes': classes, 'rawText': raw_text}
