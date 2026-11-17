import pytest

from common import KitError, clean_word
from build import resolve_ref

WORDS = [
    {"w": "¿El", "clean": "el", "a": 0.10, "end": 0.30},
    {"w": "17", "clean": "17", "a": 0.30, "end": 0.60},
    {"w": "Inteligencia", "clean": "inteligencia", "a": 1.00, "end": 1.60},
]


def test_clean_word_strips_accents_and_signs():
    assert clean_word("¿Está?") == "esta"
    assert clean_word("Año,") == "año"
    assert clean_word("IA.") == "ia"


def test_ref_by_index_and_word():
    assert resolve_ref("2:inteligencia", WORDS, 10.0) == pytest.approx(1.0)


def test_ref_word_check_ignores_case_and_accents():
    assert resolve_ref("2:Inteligéncia", WORDS, 10.0) == pytest.approx(1.0)


def test_ref_wrong_word_fails_loudly():
    with pytest.raises(KitError, match="word 2 is"):
        resolve_ref("2:artificial", WORDS, 10.0)


def test_ref_offset_seconds():
    assert resolve_ref("1:17+0.25", WORDS, 10.0) == pytest.approx(0.55)
    assert resolve_ref("1:17-0.1", WORDS, 10.0) == pytest.approx(0.20)


def test_ref_plain_int_and_special():
    assert resolve_ref(1, WORDS, 10.0) == pytest.approx(0.30)
    assert resolve_ref("start", WORDS, 10.0) == 0.0
    assert resolve_ref("end", WORDS, 10.0) == 10.0


def test_ref_out_of_range():
    with pytest.raises(KitError, match="out of range"):
        resolve_ref("9:x", WORDS, 10.0)


def test_ref_garbage():
    with pytest.raises(KitError, match="not a word reference"):
        resolve_ref("hello", WORDS, 10.0)
