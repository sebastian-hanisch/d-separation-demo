"""Presets: Vollständigkeit, gültige Werte, Zustandsbereinigung; Reglergrenzen und Hilfen."""

import dsep_constants as C
import dsep_presets as P


def test_every_preset_has_help_and_all_keys():
    assert set(C.PRESETS) == set(C.PRESET_HELP)
    for name, p in C.PRESETS.items():
        assert set(p) == {"world", "x", "y", "z", "scope", "n", "seed"}, name
        assert C.PRESET_HELP[name]


def test_preset_values_are_valid():
    for name, p in C.PRESETS.items():
        n = len(C.WORLDS[p["world"]]["nodes"])
        assert p["x"] != p["y"] and all(0 <= v < n for v in (p["x"], p["y"], *p["z"])) and p["x"] not in p["z"] and p["y"] not in p["z"], name
        assert p["scope"] in C.SCOPE_CHOICES and C.N_MIN <= p["n"] <= C.N_MAX and (p["n"] - C.N_MIN) % C.N_STEP == 0, name
        assert 0 <= p["seed"] <= C.SEED_MAX


def test_default_preset_is_the_default_world_and_every_world_has_a_preset():
    assert C.PRESETS["6-Knoten-Beispiel (Voreinstellung)"]["world"] == C.DEFAULT_WORLD
    assert {p["world"] for p in C.PRESETS.values()} == set(C.WORLDS)


def test_edge_key_helpers_round_trip():
    assert P.parse_edge(P.edge_key(2, 5)) == (2, 5)
    assert P.all_edge_keys("Kette") == ["0-1", "0-2", "1-2"]
    assert P.true_edge_keys("Kette") == ["0-1", "1-2"]
    assert len(P.all_edge_keys("6-Knoten-Beispiel")) == 15 and P.n_nodes("6-Knoten-Beispiel") == 6


def test_bounds_and_step_grid():
    assert P.bounds("n_slider") == (C.N_MIN, C.N_MAX) and P.bounds("seed_input") == (0, C.SEED_MAX)
    assert C.DEFAULT_N in range(C.N_MIN, C.N_MAX + 1, C.N_STEP)


def test_experiment_constants_are_consistent():
    assert C.MISSING_EDGE in C.SIX["coefs"] and C.EXTRA_EDGE not in C.SIX["coefs"]
    assert 0.2 in C.EXP_POWER_COEFS and 0.1 in C.EXP_POWER_COEFS and 200 in C.EXP_POWER_NS and 500 in C.EXP_POWER_NS
    assert C.EXP_MULTI_N in C.EXP_CLAIM_NS
