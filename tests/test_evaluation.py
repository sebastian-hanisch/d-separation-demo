"""Auswertung: Welten, Teilkorrelation, Fisher-z, Analyse der Einstellungen, Struktur der Experimente (klein gerechnet), Verdikte an handgesetzten Werten."""

import numpy as np
import pytest

import dsep_constants as C
import dsep_evaluation as ev
import dsep_graph as G
from kausal_generator import SplitMix64


def six_edges():
    return tuple(sorted(C.WORLDS["6-Knoten-Beispiel"]["coefs"]))


# ----------------------------------------------------------------------------- Formatierung und Welten

def test_de_and_signed():
    assert ev.de(1.5, 1) == "1,5" and ev.de(-0.05, 2) == "−0,05"
    assert ev.signed(0.0, 1) == "+0,0" and ev.signed(-1.0135, 2) == "−1,01"


@pytest.mark.parametrize("world", C.WORLD_ORDER)
def test_every_world_is_a_valid_acyclic_diagram_with_a_valid_query(world):
    w = C.WORLDS[world]
    n = len(w["nodes"])
    assert len(w["pos"]) == n and all(0 <= i < j < n for (i, j) in w["coefs"])
    x, y, z = w["query"]
    assert x != y and x not in z and y not in z and all(0 <= v < n for v in (x, y, *z))
    scm = ev.world_scm(world)
    assert scm.names == w["nodes"] and G.edges_of(scm.parents) == tuple(sorted(w["coefs"]))
    assert ev.true_parents(world) == scm.parents


def test_world_scm_coefficients_can_be_overridden_but_not_extended():
    scm = ev.world_scm("6-Knoten-Beispiel", {C.MISSING_EDGE: 0.2})
    j = C.MISSING_EDGE[1]
    assert scm.coefs[j][scm.parents[j].index(C.MISSING_EDGE[0])] == 0.2
    assert G.edges_of(scm.parents) == six_edges()


def test_population_cov_of_a_chain_by_hand():
    scm = ev.world_scm("Kette")
    cov = ev.population_cov(scm)
    assert cov[0, 0] == pytest.approx(1.0) and cov[1, 1] == pytest.approx(1.0 + 0.64) and cov[0, 1] == pytest.approx(0.8)
    assert cov[2, 2] == pytest.approx(1.0 + 0.64 * (1.0 + 0.64)) and cov[0, 2] == pytest.approx(0.64)


def test_sample_covariances_approach_the_population_covariance():
    scm = ev.world_scm("6-Knoten-Beispiel")
    sc = ev.sample_covariances(scm, 40000, SplitMix64(3))[0]
    assert np.allclose(sc, ev.population_cov(scm), atol=0.08)
    assert ev.sample_covariances(scm, 50, SplitMix64(3), reps=4).shape == (4, 6, 6)


# ----------------------------------------------------------------------------- Teilkorrelation und Test

def test_partial_correlation_collider_by_hand():
    """A, B unabhängig N(0,1), C = A + B + 0,5ε: Teilkorrelation von A, B gegeben C ist -0,8."""
    cov = np.array([[1, 0, 1], [0, 1, 1], [1, 1, 2.25]])
    assert float(ev.partial_correlations(cov, 0, 1, (2,))) == pytest.approx(-0.8)
    assert float(ev.partial_correlations(cov, 0, 1, ())) == pytest.approx(0.0)
    assert float(ev.partial_correlations(cov, 0, 2, ())) == pytest.approx(1.0 / 1.5)


def test_partial_correlations_accept_a_batch_and_a_single_matrix():
    cov = np.array([[1, 0.5, 0.3], [0.5, 1, 0.2], [0.3, 0.2, 1]])
    single = ev.partial_correlations(cov, 0, 1, (2,))
    batch = ev.partial_correlations(np.stack([cov, cov]), 0, 1, (2,))
    assert batch.shape == (2,) and batch[0] == pytest.approx(float(single))


def test_fisher_p_value_properties():
    p = ev.fisher_p_values(np.array([0.0, 0.1, -0.1, 0.9]), 500, 2)
    assert p[0] == pytest.approx(1.0) and p[1] == pytest.approx(p[2]) and p[3] < 1e-100 and p[1] < 0.05
    assert ev.fisher_p_values(np.array([0.1]), 200, 2)[0] > ev.fisher_p_values(np.array([0.1]), 2000, 2)[0]
    assert np.isfinite(ev.fisher_p_values(np.array([1.0]), 50, 1)[0])                  # r = ±1 wird geklammert


def test_family_rejected_raw_and_bonferroni():
    p = np.array([[0.04, 0.5, 0.6, 0.7], [0.001, 0.5, 0.6, 0.7], [0.5, 0.5, 0.5, 0.5]])
    assert ev.family_rejected(p).tolist() == [True, True, False]
    assert ev.family_rejected(p, bonferroni=True).tolist() == [False, True, False]        # 0,05 / 4 = 0,0125
    assert ev.family_rejected(np.zeros((2, 0))).tolist() == [False, False]


def test_family_rejected_with_one_statement_and_with_none_under_bonferroni():
    assert ev.family_rejected(np.array([[0.01], [0.2]])).tolist() == [True, False]
    assert ev.family_rejected(np.array([[0.01], [0.2]]), bonferroni=True).tolist() == [True, False]
    assert ev.family_rejected(np.array([[0.04]]), bonferroni=True).tolist() == [True]       # alpha / 1
    assert ev.family_rejected(np.zeros((3, 0)), bonferroni=True).tolist() == [False, False, False]


def test_sample_covariances_equal_numpy_cov_of_the_same_sample():
    from kausal_generator import sample

    scm = ev.world_scm("6-Knoten-Beispiel")
    cov = ev.sample_covariances(scm, 30, SplitMix64(7), reps=2)
    d = sample(scm, 30, SplitMix64(7), reps=2)
    for r in range(2):
        expected = np.cov(np.stack([d[name][r] for name in scm.names]))
        assert np.allclose(cov[r], expected, rtol=1e-12, atol=1e-12)


def test_signed_uses_the_correct_sign_around_zero():
    assert ev.signed(-0.5, 2) == "−0,50" and ev.signed(0.5, 2) == "+0,50" and ev.signed(-0.004, 2) == "−0,00"


def test_verdict_claim_uses_the_largest_sample_size():
    rows = [{"variant": v, "n": n, "bonf": b} for n, vals in ((200, (0.03, 0.9, 0.04)), (2000, (0.05, 1.0, 0.04)))
            for v, b in zip(("wahres Diagramm", "Pfeil Faktor → Servicegrad fehlt", "Pfeil Region → Servicegrad überzählig"), vals)]
    text = ev.verdict_claim(rows)[1]
    assert "n = 2000" in text and "100 %" in text and "90 %" not in text


def test_test_statements_without_statements_returns_empty_arrays():
    r, p = ev.test_statements(np.eye(3), [], 100)
    assert r.shape == (1, 0) and p.shape == (1, 0)


# ----------------------------------------------------------------------------- Analyse

def test_analysis_of_the_default_settings_is_internally_consistent():
    a = ev.analyse(ev.Settings())
    assert a.separated and len(a.paths) == 3 and a.n_basis == 12 and a.n_cond2 == 29 and not a.complete
    assert a.missing == () and a.extra == ()
    assert len(a.statements) == 12 and all(row.holds for row in a.statements)
    assert a.rejected_raw == sum(r.reject_raw for r in a.statements) and a.rejected_bonf <= a.rejected_raw
    assert all(0.0 <= r.p <= 1.0 and -1.0 <= r.r <= 1.0 for r in a.statements)


def test_scope_all_uses_the_larger_statement_set():
    a = ev.analyse(ev.Settings(scope="alle"))
    assert len(a.statements) == 29 > ev.analyse(ev.Settings()).n_basis


def test_removed_arrow_is_reported_and_rejected():
    edges = tuple(e for e in six_edges() if e != C.MISSING_EDGE)
    a = ev.analyse(ev.Settings(edges=edges, n=2000))
    assert a.missing == (C.MISSING_EDGE,) and a.extra == () and a.rejected_bonf >= 1
    assert any(not row.holds for row in a.statements)
    assert ev.verdict_check(a)[0] == "warning"


def test_added_arrow_is_reported_as_extra_and_all_its_statements_hold():
    edges = tuple(sorted(set(six_edges()) | {C.EXTRA_EDGE}))
    a = ev.analyse(ev.Settings(edges=edges, scope="alle"))
    assert a.extra == (C.EXTRA_EDGE,) and a.missing == () and all(row.holds for row in a.statements)


def test_missing_and_extra_arrows_are_listed_in_ascending_order():
    truth = set(six_edges())
    drop = {(0, 2), (3, 5)}
    add = {(0, 5), (1, 5)}
    a = ev.analyse(ev.Settings(edges=tuple(sorted((truth - drop) | add))))
    assert a.missing == ((0, 2), (3, 5)) and a.extra == ((0, 5), (1, 5))


def test_complete_diagram_has_no_statements_and_an_info_verdict():
    world = "Stück-1-Diagramm"
    a = ev.analyse(ev.Settings(world=world, edges=tuple(sorted(C.WORLDS[world]["coefs"])), x=1, y=2, z=()))
    assert a.complete and a.statements == [] and not a.separated
    kind, text = ev.verdict_check(a)
    assert kind == "info" and "keine Unabhängigkeit" in text
    assert ev.verdict_query(a)[0] == "info"


def test_empty_diagram_separates_every_pair():
    a = ev.analyse(ev.Settings(world="Collider", edges=(), x=0, y=1, z=(2,)))
    assert a.separated and a.paths == [] and a.missing == tuple(sorted(C.WORLDS["Collider"]["coefs"]))


def test_query_verdicts_and_texts():
    sep = ev.analyse(ev.Settings())
    kind, text = ev.verdict_query(sep)
    assert kind == "success" and "d-getrennt" in text and "Region und Wetter" in text
    con = ev.analyse(ev.Settings(z=(4,)))
    kind, text = ev.verdict_query(con)
    assert kind == "info" and "verbunden" in text and "gegeben Lieferverzug" in text


def test_collider_opens_in_the_six_node_world_by_the_analysis_and_the_data():
    base = ev.analyse(ev.Settings(n=5000, seed=5))
    opened = ev.analyse(ev.Settings(n=5000, seed=5, z=(4,)))
    assert base.separated and not opened.separated
    assert sum(1 for p in opened.paths if not p.blocked) == 1
    cov = ev.population_cov(ev.world_scm("6-Knoten-Beispiel"))
    assert abs(float(ev.partial_correlations(cov, 0, 1, ()))) < 1e-12 and float(ev.partial_correlations(cov, 0, 1, (4,))) == pytest.approx(-0.329, abs=0.001)
    assert float(ev.partial_correlations(cov, 0, 1, (5,))) == pytest.approx(-0.166, abs=0.001)


def test_statement_and_path_texts():
    names = C.WORLDS["6-Knoten-Beispiel"]["nodes"]
    assert ev.statement_text(names, (0, 1, ())) == "Region ⊥ Wetter"
    assert ev.statement_text(names, (0, 3, (2,))) == "Region ⊥ Faktor | Schwankung"
    (p,) = [q for q in G.explain_paths(ev.true_parents("Kette"), 0, 2, (1,))]
    assert ev.path_text(C.WORLDS["Kette"]["nodes"], p) == "Faktor → Bestand → Servicegrad"
    assert "Bestand ist vorgegeben" in ev.path_reason(C.WORLDS["Kette"]["nodes"], p)
    (q,) = G.explain_paths(ev.true_parents("Collider"), 0, 1, ())
    assert "Collider Lieferverzug" in ev.path_reason(C.WORLDS["Collider"]["nodes"], q)


# ----------------------------------------------------------------------------- Experimente

def test_collider_experiment_rows_and_values():
    res = ev.collider_experiment(n=60000)
    rows = {r["label"]: r for r in res["rows"]}
    assert rows["ohne Bedingung"]["value"] == pytest.approx(0.0, abs=1e-12) and rows["ohne Bedingung"]["separated"] is True
    assert rows["gegeben C (der Collider)"]["value"] == pytest.approx(-0.8)
    assert rows["gegeben D (ein Nachfahre des Colliders)"]["value"] == pytest.approx(-2.0 / 3.0, abs=1e-9)
    assert -0.45 < rows["bei Auswahl C > 0 (Selektion)"]["value"] < -0.35
    assert "60.000" in rows["bei Auswahl C > 0 (Selektion)"]["kind"]


def test_six_variants_differ_by_exactly_one_arrow():
    v = ev.six_variants()
    t = set(G.edges_of(v["wahres Diagramm"]))
    assert set(G.edges_of(v["Pfeil Faktor → Servicegrad fehlt"])) == t - {C.MISSING_EDGE}
    assert set(G.edges_of(v["Pfeil Region → Servicegrad überzählig"])) == t | {C.EXTRA_EDGE}


def test_statement_counts_by_hand():
    rows = {r["world"]: r for r in ev.statement_counts()}
    assert rows["Kette"]["all"] == 1 and rows["Gabel"]["all"] == 1 and rows["Collider"]["all"] == 1
    assert rows["Collider mit Nachfahre"]["all"] == 5 and rows["Collider mit Nachfahre"]["basis"] == 3
    assert rows["Stück-1-Diagramm"]["all"] == 0 and rows["Stück-1-Diagramm"]["complete"] is True
    assert rows["6-Knoten-Beispiel"]["basis"] == 12 and rows["6-Knoten-Beispiel"]["cond2"] == 29 and rows["6-Knoten-Beispiel"]["all"] == 48


def test_claim_experiment_structure_and_direction():
    rows = ev.claim_experiment(ns=(500,), reps=80)
    by = {r["variant"]: r for r in rows}
    assert set(by) == set(ev.six_variants())
    assert by["Pfeil Faktor → Servicegrad fehlt"]["bonf"] > 0.9 and by["Pfeil Faktor → Servicegrad fehlt"]["new"] == 4
    assert by["wahres Diagramm"]["new"] == 0 and by["wahres Diagramm"]["k"] == 12
    assert by["Pfeil Region → Servicegrad überzählig"]["k"] == 11
    for r in rows:
        assert r["bonf"] <= r["raw"]


def test_equivalence_experiment_numbers():
    rows = {r["nodes"]: r for r in ev.equivalence_experiment()}
    assert (rows[3]["dags"], rows[3]["classes"], rows[3]["singles"], rows[3]["largest"], rows[3]["complete"]) == (25, 11, 4, 6, 6)
    assert (rows[4]["dags"], rows[4]["classes"], rows[4]["singles"], rows[4]["largest"], rows[4]["complete"]) == (543, 185, 59, 24, 24)


def test_multitest_experiment_structure():
    rows = ev.multitest_experiment(reps=100)
    assert [r["k"] for r in rows] == [12, 29]
    for r in rows:
        assert r["bonf"] <= r["raw"] <= 1.0 and r["naive"] == pytest.approx(1 - 0.95 ** r["k"])
    assert rows[1]["raw"] > 0.2 and rows[1]["bonf"] < 0.12


def test_power_experiment_rises_with_n_and_with_the_coefficient():
    rows = ev.power_experiment(coefs=(0.1, 0.5), ns=(200, 1000), reps=60)
    at = {(r["c"], r["n"]): r["power"] for r in rows}
    assert at[(0.1, 1000)] > at[(0.1, 200)] and at[(0.5, 200)] > at[(0.1, 200)] and at[(0.5, 1000)] > 0.95


# ----------------------------------------------------------------------------- Verdikte an handgesetzten Werten

def test_verdict_texts_quote_the_numbers_they_are_given():
    res = {"rows": [{"label": "ohne Bedingung", "value": -0.0002}, {"label": "gegeben C (der Collider)", "value": -0.8},
                    {"label": "gegeben D (ein Nachfahre des Colliders)", "value": -0.667}, {"label": "bei Auswahl C > 0 (Selektion)", "value": -0.394}]}
    kind, text = ev.verdict_collider(res)
    assert kind == "warning" and "−0,80" in text and "−0,67" in text and "−0,39" in text
    rows = [{"variant": v, "n": 2000, "bonf": b} for v, b in (("wahres Diagramm", 0.05), ("Pfeil Faktor → Servicegrad fehlt", 1.0),
                                                                ("Pfeil Region → Servicegrad überzählig", 0.04))]
    assert "100 %" in ev.verdict_claim(rows)[1] and "5 %" in ev.verdict_claim(rows)[1] and "4 %" in ev.verdict_claim(rows)[1]
    kind, text = ev.verdict_multitest([{"scope": "x", "k": 12, "raw": 0.4, "bonf": 0.036, "naive": 0.46}, {"scope": "y", "k": 29, "raw": 0.47, "bonf": 0.03, "naive": 0.77}])
    assert kind == "warning" and "29 Aussagen" in text and "47 %" in text and "77 %" in text and "3,0 %" in text
    rows = [{"c": c, "n": n, "power": p} for c, n, p in ((0.2, 200, 0.5), (0.2, 500, 0.96), (0.1, 500, 0.31))]
    text = ev.verdict_power(rows)[1]
    assert "50 %" in text and "96 %" in text and "31 %" in text
