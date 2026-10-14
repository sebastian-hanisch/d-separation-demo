"""End-to-end Smoke-Test via Streamlits offiziellem AppTest-Framework: lädt app.py mit den Standardeinstellungen, klickt jeden Preset-Button, fährt jeden
Slider an seine Grenzen, wechselt Welt und Pfeile und prüft, dass kein Python-Fehler auftritt (insbesondere StreamlitDuplicateElementId bei st.plotly_chart
ohne eindeutiges key= und Auswahllisten, deren gespeicherter Wert in der neuen Welt nicht mehr vorkommt)."""

import os

from streamlit.testing.v1 import AppTest

import dsep_constants as C

APP_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
TIMEOUT = 240


def _fresh_app() -> AppTest:
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    return at


def test_app_loads_without_exception_and_shows_the_default_world():
    at = _fresh_app()
    assert at.selectbox(key="world_select").value == C.DEFAULT_WORLD
    assert {m.label for m in at.metric} == {"Frage", "Aussagen (Basis)", "Abgelehnt (roh)", "Abgelehnt (Bonferroni)"}
    assert at.metric[0].value == "getrennt"


def test_every_button_click_does_not_raise():
    labels = [b.label for b in _fresh_app().button]
    assert labels, "keine Buttons gefunden"
    for index, label in enumerate(labels):
        at = _fresh_app()
        at.button[index].click().run(timeout=TIMEOUT)
        assert not at.exception, (label, [str(e) for e in at.exception])


def test_the_slider_at_its_min_and_max_does_not_raise():
    for edge in ("min", "max"):
        at = _fresh_app()
        s = at.slider(key="n_slider")
        s.set_value(int(s.min if edge == "min" else s.max)).run(timeout=TIMEOUT)
        assert not at.exception, (edge, [str(e) for e in at.exception])


def test_every_preset_is_applied_to_the_widgets():
    labels = {b.label: i for i, b in enumerate(_fresh_app().button)}
    for name, preset in C.PRESETS.items():
        at = _fresh_app()
        at.button[labels[name]].click().run(timeout=TIMEOUT)
        assert not at.exception, (name, [str(e) for e in at.exception])
        assert at.selectbox(key="world_select").value == preset["world"]
        assert at.selectbox(key="x_select").value == preset["x"] and at.selectbox(key="y_select").value == preset["y"]
        assert at.multiselect(key="z_select").value == list(preset["z"])
        assert at.slider(key="n_slider").value == preset["n"]
        expected = len(C.WORLDS[preset["world"]]["coefs"])
        assert len(at.multiselect(key="edges_select").value) == expected


def test_changing_the_world_resets_the_drawn_diagram_and_the_question():
    at = _fresh_app()
    at.selectbox(key="world_select").select("Kette").run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    assert sorted(at.multiselect(key="edges_select").value) == ["0-1", "1-2"]
    assert (at.selectbox(key="x_select").value, at.selectbox(key="y_select").value, at.multiselect(key="z_select").value) == (0, 2, [1])
    assert at.metric[0].value == "getrennt"


def test_conditioning_on_the_collider_opens_the_path():
    at = _fresh_app()
    at.multiselect(key="z_select").set_value([4]).run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    assert at.metric[0].value == "verbunden"
    at.multiselect(key="z_select").set_value([2]).run(timeout=TIMEOUT)
    assert at.metric[0].value == "getrennt"


def test_choosing_x_equal_to_y_does_not_raise_and_keeps_two_different_nodes():
    at = _fresh_app()
    y = at.selectbox(key="y_select").value
    at.selectbox(key="x_select").set_value(y).run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    assert at.selectbox(key="x_select").value != at.selectbox(key="y_select").value
    assert at.selectbox(key="x_select").value not in at.multiselect(key="z_select").value


def test_removing_a_true_arrow_is_rejected_by_the_data():
    at = _fresh_app()
    edges = [k for k in at.multiselect(key="edges_select").value if k != "3-5"]
    at.multiselect(key="edges_select").set_value(edges).run(timeout=TIMEOUT)
    at.slider(key="n_slider").set_value(2000).run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    assert any("abgelehnt" in w.value for w in at.warning)


def test_world_with_fewer_nodes_after_a_selection_in_a_larger_one_does_not_raise():
    at = _fresh_app()
    at.selectbox(key="x_select").set_value(5).run(timeout=TIMEOUT)
    at.multiselect(key="z_select").set_value([2, 3]).run(timeout=TIMEOUT)
    at.selectbox(key="world_select").select("Collider").run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    assert at.selectbox(key="x_select").value < 3 and all(v < 3 for v in at.multiselect(key="z_select").value)


def test_removing_every_arrow_does_not_raise():
    at = _fresh_app()
    at.multiselect(key="edges_select").set_value([]).run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    assert at.metric[0].value == "getrennt"


def test_statements_scope_all_does_not_raise():
    at = _fresh_app()
    at.selectbox(key="scope_select").select("alle").run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    assert at.metric[2].value.endswith("von 29")


def test_the_power_experiment_runs_only_after_the_click():
    at = _fresh_app()
    assert "power_done" not in at.session_state
    labels = {b.label: i for i, b in enumerate(at.button)}
    key = next(k for k in labels if k.startswith("🧮"))
    at.button[labels[key]].click().run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    assert at.session_state["power_done"] is True
    assert any("Koeffizient 0,2" in i.value for i in at.info)


def test_pdf_is_created_only_after_the_click():
    at = _fresh_app()
    assert "pdf_made" not in at.session_state
    at.button(key="pdf_make").click().run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    settings, data = at.session_state["pdf_made"]
    assert data[:5] == b"%PDF-" and len(data) > 1000


def test_permalink_values_are_taken_and_invalid_ones_cleaned():
    at = AppTest.from_file(APP_PATH, default_timeout=TIMEOUT)
    at.query_params["w"] = "Kette"
    at.query_params["e"] = "0-1,1-2,7-9,abc"
    at.query_params["x"] = "2"
    at.query_params["y"] = "2"
    at.query_params["z"] = "0,9"
    at.query_params["n"] = "999999"
    at.query_params["sc"] = "irgendwas"
    at.run()
    assert not at.exception, [str(e) for e in at.exception]
    assert at.selectbox(key="world_select").value == "Kette"
    assert sorted(at.multiselect(key="edges_select").value) == ["0-1", "1-2"]
    assert at.selectbox(key="x_select").value == 2 and at.selectbox(key="y_select").value != 2
    assert 9 not in at.multiselect(key="z_select").value
    assert at.slider(key="n_slider").value == C.N_MAX and at.selectbox(key="scope_select").value == "basis"


def test_unknown_world_in_the_permalink_is_ignored():
    at = AppTest.from_file(APP_PATH, default_timeout=TIMEOUT)
    at.query_params["w"] = "Nirgendwo"
    at.run()
    assert not at.exception, [str(e) for e in at.exception]
    assert at.selectbox(key="world_select").value == C.DEFAULT_WORLD


def test_the_address_bar_mirrors_the_settings():
    at = _fresh_app()
    at.selectbox(key="world_select").select("Gabel").run(timeout=TIMEOUT)
    assert at.query_params["w"] in ("Gabel", ["Gabel"])
