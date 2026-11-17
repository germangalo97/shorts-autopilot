import pytest

from common import KitError
from build import build_props, layout_lines, LINES_BOTTOM, NARROW_BELOW_Y, NARROW_WIDTH, WIDE_WIDTH, char_width

STYLE = {"accent": "#D7FF3E", "accent2": "#FFD23F", "danger": "#FF3B3B", "ok": "#2BD46B", "text": "#FFFFFF",
         "muted": "#8A8F98", "bg": "#0E0E0E", "panel": "#16181D", "font": "anton", "subtitleFont": "inter"}


def words(n=40, step=0.4):
    return [{"w": f"w{i}", "clean": f"w{i}", "a": round(i * step, 3), "end": round(i * step + 0.35, 3),
             "endsSentence": i % 8 == 7} for i in range(n)]


def config():
    return {"style": STYLE, "labels": {"badge": "MADE WITH AI", "aiImage": "AI-GENERATED IMAGE"}}


def test_layout_stacks_lines_downward_and_fits_width():
    lines = layout_lines([{"text": "THE 17TH OF"}, {"text": "NOVEMBER", "size": 170}], "anton")
    assert lines[0]["y"] < lines[1]["y"]
    for line in lines:
        limit = NARROW_WIDTH if line["y"] + line["size"] * 0.46 >= NARROW_BELOW_Y else WIDE_WIDTH
        assert len(line["text"]) * line["size"] * char_width("anton") <= limit + 1


def test_layout_long_line_is_shrunk():
    lines = layout_lines([{"text": "A VERY VERY LONG LINE OF TEXT", "size": 200}], "anton")
    assert lines[0]["size"] < 200


def test_layout_never_goes_below_bottom_limit():
    lines = layout_lines([{"text": "ONE", "size": 300}, {"text": "TWO", "size": 300}, {"text": "THREE", "size": 300},
                          {"text": "FOUR", "size": 300}], "anton")
    last = lines[-1]
    assert last["y"] + last["size"] * 0.46 <= LINES_BOTTOM + 1


def test_lines_below_the_button_column_move_left():
    lines = layout_lines([{"text": "A"}, {"text": "B"}, {"text": "C"}, {"text": "D"}], "anton")
    for line in lines:
        assert line["x"] == (495 if line["y"] + line["size"] * 0.46 >= NARROW_BELOW_Y else 540)


def test_build_resolves_scenes_beats_and_colors():
    spec = {
        "hits": ["3:w3"],
        "scenes": [
            {"from": "start", "background": {"image": "a.png"}, "kicker": {"text": "PROOF 1", "color": "accent"},
             "beats": [{"at": "start", "lines": ["HELLO", {"text": "WORLD", "color": "danger", "at": "2:w2"}]},
                       {"at": "4:w4", "lines": ["NEXT"]}]},
            {"from": "10:w10", "background": {"color": "panel"}, "beats": [{"lines": ["END"]}]},
        ],
    }
    props = build_props(spec, words(), {}, config(), duration=16.0, images={"a.png"})
    s0, s1 = props["scenes"]
    assert s0["from"] == 0 and s0["to"] == 120 and s1["from"] == 120 and s1["to"] == props["frames"]
    assert props["frames"] == 480
    b0, b1 = s0["beats"]
    assert b0["to"] == b1["from"] == 48
    assert b0["lines"][0]["from"] < 0  # first frame already shows the hook (possible cover)
    assert b0["lines"][1]["from"] == 24 and b0["lines"][1]["color"] == "#FF3B3B"
    assert s0["kicker"]["background"] == "#D7FF3E"
    assert s0["background"]["aiGenerated"] is True
    assert s1["background"]["color"] == "#16181D"
    assert props["hits"] == [36]
    assert props["badge"]["text"] == "MADE WITH AI"


def test_build_rejects_missing_image():
    spec = {"scenes": [{"from": "start", "background": {"image": "missing.png"}, "beats": [{"lines": ["X"]}]}]}
    with pytest.raises(KitError, match="missing.png"):
        build_props(spec, words(), {}, config(), duration=16.0, images=set())


def test_build_texts_must_come_from_texts_json():
    spec = {"scenes": [{"from": "start", "beats": [{"lines": ["$t:hour"]}]}]}
    props = build_props(spec, words(), {"hour": "14:20"}, config(), duration=16.0, images=set())
    assert props["scenes"][0]["beats"][0]["lines"][0]["text"] == "14:20"
    with pytest.raises(KitError, match="texts.json"):
        build_props(spec, words(), {}, config(), duration=16.0, images=set())


def test_build_scenes_must_be_in_order():
    spec = {"scenes": [{"from": "start", "beats": [{"lines": ["A"]}]}, {"from": "10:w10", "beats": [{"lines": ["B"]}]},
                       {"from": "2:w2", "beats": [{"lines": ["C"]}]}]}
    with pytest.raises(KitError, match="order"):
        build_props(spec, words(), {}, config(), duration=16.0, images=set())


def test_build_first_scene_must_start_at_zero():
    spec = {"scenes": [{"from": "2:w2", "beats": [{"lines": ["A"]}]}]}
    with pytest.raises(KitError, match="first scene"):
        build_props(spec, words(), {}, config(), duration=16.0, images=set())


def test_build_elements_get_defaults_and_frames():
    spec = {"scenes": [{"from": "start", "beats": [{"lines": ["A"]}], "elements": [
        {"type": "checklist", "items": [{"text": "RADIO", "ok": True, "at": "1:w1"}, {"text": "PHONES", "ok": False, "at": "2:w2"}]},
        {"type": "timer", "text": "1 MINUTE", "at": "3:w3"},
        {"type": "nonsense"},
    ]}]}
    with pytest.raises(KitError, match="nonsense"):
        build_props(spec, words(), {}, config(), duration=16.0, images=set())
    spec["scenes"][0]["elements"].pop()
    props = build_props(spec, words(), {}, config(), duration=16.0, images=set())
    checklist, timer = props["scenes"][0]["elements"]
    assert [i["from"] for i in checklist["items"]] == [12, 24]
    assert timer["from"] == 36 and timer["fillBy"] > timer["from"] and timer["to"] == props["frames"]


def test_build_ai_label_can_be_turned_off_for_own_photos():
    spec = {"scenes": [{"from": "start", "background": {"image": "me.png", "ai": False}, "beats": [{"lines": ["A"]}]}]}
    props = build_props(spec, words(), {}, config(), duration=16.0, images={"me.png"})
    assert props["scenes"][0]["background"]["aiGenerated"] is False


def test_layout_custom_top_moves_lines_down_and_is_bounded():
    default = layout_lines([{"text": "A"}], "anton")
    lower = layout_lines([{"text": "A"}], "anton", top=820)
    assert lower[0]["y"] > default[0]["y"]
    with pytest.raises(KitError, match="top"):
        layout_lines([{"text": "A"}], "anton", top=1500)


def test_a_line_whose_bottom_crosses_into_the_button_rows_is_narrow():
    lines = layout_lines([{"text": "NO ME CREAS", "size": 190}, {"text": "A MI TAMPOCO", "size": 150}], "anton")
    second = lines[1]
    assert second["y"] < NARROW_BELOW_Y < second["y"] + second["size"] * 0.46
    assert second["x"] == 495 and len(second["text"]) * second["size"] * char_width("anton") <= NARROW_WIDTH + 1
