from sound_plan import make_plan, MIN_GAP_S


def props():
    return {
        "frames": 600,
        "hits": [90],
        "scenes": [
            {"from": 0, "to": 300, "beats": [{"from": 0, "to": 150, "lines": [{"from": -12}, {"from": 30}]},
                                             {"from": 150, "to": 300, "lines": [{"from": 150}]}],
             "elements": [{"type": "checklist", "from": 0, "to": 300, "items": [{"from": 200}, {"from": 240}]}]},
            {"from": 300, "to": 600, "beats": [{"from": 300, "to": 600, "lines": [{"from": 300}]}],
             "elements": [{"type": "search", "from": 300, "to": 600, "typeFrom": 320, "resultFrom": 400}]},
        ],
    }


def kinds_at(plan, t):
    return {e["effect"] for e in plan["effects"] if abs(e["t"] - t) < 1e-3}


def test_plan_has_scene_beat_line_hit_and_element_sounds():
    plan = make_plan(props(), {}, {"file": "song.mp3"})
    assert "impact" in kinds_at(plan, 0.0)
    assert "whoosh_short" in kinds_at(plan, 10.0)  # second scene
    assert "text_hit" in kinds_at(plan, 5.0)  # second beat
    assert "pop" in kinds_at(plan, 1.0)  # delayed line
    assert "impact" in kinds_at(plan, 3.0)  # hit
    assert "click" in kinds_at(plan, 200 / 30)  # checklist row
    assert "typing" in kinds_at(plan, 320 / 30)
    assert "beep_low" in kinds_at(plan, 400 / 30)
    whoosh = [e for e in plan["effects"] if e["effect"] == "whoosh_short"][0]
    assert whoosh["align"] == "peak"


def test_plan_has_no_duplicates_too_close():
    plan = make_plan(props(), {"sound": {"extra": [{"t": 3.0, "effect": "impact", "db": -8}]}}, {"file": "song.mp3"})
    same = sorted(e["t"] for e in plan["effects"] if e["effect"] == "impact")
    assert all(b - a >= MIN_GAP_S for a, b in zip(same, same[1:]))


def test_plan_music_settings_and_cuts():
    spec = {"music": {"cuts": [[2.0, 3.0]], "stop": 4.0, "resume": 6.0}}
    plan = make_plan(props(), spec, {"file": "song.mp3", "db": -12})
    m = plan["music"]
    assert m["file"] == "song.mp3" and m["db"] == -12
    assert {"t": 2.0, "db": -40} in m["automation"] and m["stop"]["t"] == 4.0 and m["resume"] == 6.0


def test_plan_effects_sorted_and_inside_video():
    plan = make_plan(props(), {"sound": {"extra": [{"t": 99, "effect": "pop"}]}}, {"file": "song.mp3"})
    ts = [e["t"] for e in plan["effects"]]
    assert ts == sorted(ts) and max(ts) <= 20.0
