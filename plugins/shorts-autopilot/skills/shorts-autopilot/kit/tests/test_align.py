from align import align, script_words


def test_align_equal_and_replaced_words():
    script = [{"w": w, "clean": w, "block": "b", "local_sentence": 0, "endsSentence": False} for w in ["hola", "claude", "mundo"]]
    heard = [{"w": "hola", "clean": "hola", "a": 0.0, "end": 0.3}, {"w": "clod", "clean": "clod", "a": 0.3, "end": 0.6},
             {"w": "mundo", "clean": "mundo", "a": 0.6, "end": 0.9}]
    out, missing, extra = align(script, heard)
    assert [w["a"] for w in out] == [0.0, 0.3, 0.6]
    assert missing == [] and extra and "claude" in extra[0]


def test_align_missing_word_gets_time_between_neighbours():
    script = [{"w": w, "clean": w, "block": "b", "local_sentence": 0, "endsSentence": False} for w in ["a", "b", "c"]]
    heard = [{"w": "a", "clean": "a", "a": 0.0, "end": 0.2}, {"w": "c", "clean": "c", "a": 0.5, "end": 0.7}]
    out, missing, _ = align(script, heard)
    assert missing == ["b"]
    assert out[0]["end"] <= out[1]["a"] <= out[2]["a"]


def test_script_words_marks_sentence_ends(tmp_path):
    import json
    p = tmp_path / "script.json"
    p.write_text(json.dumps({"blocks": [{"id": "hook", "text": "Hola. ¿Qué tal?", "style": "x"}]}), encoding="utf-8")
    ws = script_words(p)
    assert [w["endsSentence"] for w in ws] == [True, False, True]
    assert ws[1]["clean"] == "que"
