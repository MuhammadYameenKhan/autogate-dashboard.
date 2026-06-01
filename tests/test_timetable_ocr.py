"""Tests for timetable OCR text parsing (no image/Tesseract required)."""

from app.services.timetable_ocr import parse_schedule_from_text


def test_parse_line_with_day_time_course_building():
    raw = """
    Monday 08:00 - 09:30 Data Structures Block A
    Tuesday 11:00-12:30 Database Systems Building B
    """
    classes = parse_schedule_from_text(raw)
    assert len(classes) >= 2
    assert classes[0]['day'] == 'Monday'
    assert '08:00' in classes[0]['time']
    assert classes[0]['building'] == 'A'
    assert 'Data Structures' in classes[0]['course']


def test_parse_abbreviated_days():
    raw = 'Wed 14:00 - 15:30 Computer Networks Room C'
    classes = parse_schedule_from_text(raw)
    assert len(classes) == 1
    assert classes[0]['day'] == 'Wednesday'
    assert classes[0]['building'] == 'C'


def test_parse_empty_text():
    assert parse_schedule_from_text('') == []
    assert parse_schedule_from_text('   \n  ') == []
