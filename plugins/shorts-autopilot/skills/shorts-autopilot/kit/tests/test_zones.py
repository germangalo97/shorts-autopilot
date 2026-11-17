import numpy as np

from zones import covered, count_lit, split_flags, ZONES


def blank():
    return np.full((1920, 1080, 3), 14, dtype=np.uint8)


def test_blank_frame_is_clean():
    assert covered(count_lit(blank())) == []


def test_text_in_top_zone_is_flagged():
    f = blank()
    f[50:120, 300:700] = 255
    assert covered(count_lit(f)) == ["top"]


def test_text_in_button_column_is_flagged():
    f = blank()
    y0, y1, x0, x1 = ZONES["buttons"]
    f[y0 + 50:y0 + 150, x0 + 10:x0 + 100] = 255
    assert "buttons" in covered(count_lit(f))


def test_single_frame_entries_are_separated_from_lasting_problems():
    flags = {0: ["top"], 5: ["top"], 50: ["bottom"]}
    lasting, entries = split_flags(flags, 5)
    assert lasting == [0, 5] and entries == [50]
