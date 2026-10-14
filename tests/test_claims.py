"""Jede Zahl aus README.md und den App-Texten wird hier über dieselben Auswertungsfunktionen nachgerechnet (DEMO-PLAYBOOK §4).

Alle Experimente laufen über feste Zufallsströme (dsep_constants.SEED_BASE), nie über einen einzelnen Seed als Befund; die Stichprobe der Primäransicht ist
ausdrücklich eine einzelne (Seed 35). Prozentwerte mit Toleranz von 3 Punkten (300 Wiederholungen), exakte Werte mit 1e-9, damit Rundung und
Bibliotheksversionen (CI installiert ungepinnt) nichts kippen.
"""

import pytest

import dsep_constants as C
import dsep_evaluation as ev
import dsep_graph as G


def pct(x):
    return 100 * x


@pytest.fixture(scope="module")
def collider():
    return {r["label"]: r for r in ev.collider_experiment()["rows"]}


@pytest.fixture(scope="module")
def claim():
    return {(r["variant"], r["n"]): r for r in ev.claim_experiment()}


@pytest.fixture(scope="module")
def multitest():
    return {r["k"]: r for r in ev.multitest_experiment()}


@pytest.fixture(scope="module")
def power():
    return {(r["c"], r["n"]): r["power"] for r in ev.power_experiment()}


# ----------------------------------------------------------------------------- Aussagen und Standard-Stichprobe

def test_six_node_example_has_twelve_basis_statements_29_with_two_conditions_and_48_in_total():
    par = ev.true_parents("6-Knoten-Beispiel")
    assert len(G.local_markov_basis(par)) == 12 and len(G.separations(par, 2)) == 29 and len(G.separations(par, None)) == 48
    assert len(G.edges_of(par)) == 7


def test_default_sample_rejects_one_of_twelve_raw_and_none_with_bonferroni():
    a = ev.analyse(ev.Settings())
    assert a.separated and len(a.paths) == 3 and a.rejected_raw == 1 and a.rejected_bonf == 0 and len(a.statements) == 12


def test_statement_counts_by_world():
    rows = {r["world"]: r for r in ev.statement_counts()}
    assert {w: rows[w]["all"] for w in rows} == {"Kette": 1, "Gabel": 1, "Collider": 1, "Collider mit Nachfahre": 5, "Stück-1-Diagramm": 0, "6-Knoten-Beispiel": 48}


def test_all_twenty_five_and_543_diagrams_fall_into_11_and_185_classes():
    rows = {r["nodes"]: r for r in ev.equivalence_experiment()}
    assert (rows[3]["dags"], rows[3]["classes"], rows[3]["singles"], rows[3]["largest"]) == (25, 11, 4, 6)
    assert (rows[4]["dags"], rows[4]["classes"], rows[4]["singles"], rows[4]["largest"]) == (543, 185, 59, 24)
    assert pct(rows[3]["singles"] / rows[3]["dags"]) == pytest.approx(16, abs=0.5) and pct(rows[4]["singles"] / rows[4]["dags"]) == pytest.approx(11, abs=0.5)


# ----------------------------------------------------------------------------- Experiment 1: Collider

def test_experiment_1_collider_partial_correlations(collider):
    assert collider["ohne Bedingung"]["value"] == pytest.approx(0.0, abs=1e-9)
    assert collider["gegeben C (der Collider)"]["value"] == pytest.approx(-0.8, abs=1e-9)
    assert collider["gegeben D (ein Nachfahre des Colliders)"]["value"] == pytest.approx(-2 / 3, abs=1e-9)
    assert collider["bei Auswahl C > 0 (Selektion)"]["value"] == pytest.approx(-0.39, abs=0.02)


def test_the_collider_in_the_six_node_world_gives_the_numbers_of_the_assumptions_text():
    cov = ev.population_cov(ev.world_scm("6-Knoten-Beispiel"))
    assert float(ev.partial_correlations(cov, 0, 1, (4,))) == pytest.approx(-0.33, abs=0.005)
    assert float(ev.partial_correlations(cov, 0, 1, (5,))) == pytest.approx(-0.17, abs=0.005)


# ----------------------------------------------------------------------------- Experiment 2: fehlender und überzähliger Pfeil

def test_experiment_2_missing_arrow_is_always_rejected(claim):
    for n in C.EXP_CLAIM_NS:
        r = claim[("Pfeil Faktor → Servicegrad fehlt", n)]
        assert r["bonf"] == pytest.approx(1.0) and r["raw"] == pytest.approx(1.0) and r["k"] == 14 and r["new"] == 4


def test_experiment_2_true_and_extra_arrow_diagrams_are_rejected_about_equally_often(claim):
    for n in C.EXP_CLAIM_NS:
        t, e = claim[("wahres Diagramm", n)], claim[("Pfeil Region → Servicegrad überzählig", n)]
        assert t["k"] == 12 and e["k"] == 11 and e["new"] == 1 and t["new"] == 0
        assert pct(t["bonf"]) == pytest.approx(5, abs=3.5) and pct(e["bonf"]) == pytest.approx(5, abs=3.5)
        assert 30 <= pct(t["raw"]) <= 50 and 28 <= pct(e["raw"]) <= 48


# ----------------------------------------------------------------------------- Experiment 3: Mehrfachtests

def test_experiment_3_family_wise_rejection_of_the_true_diagram(multitest):
    basis, big = multitest[12], multitest[29]
    assert pct(basis["raw"]) == pytest.approx(40, abs=5) and pct(big["raw"]) == pytest.approx(47, abs=5)
    assert pct(basis["naive"]) == pytest.approx(46, abs=0.5) and pct(big["naive"]) == pytest.approx(77, abs=0.5)
    assert pct(basis["bonf"]) < 6 and pct(big["bonf"]) < 6


# ----------------------------------------------------------------------------- Experiment 4: Macht

def test_experiment_4_power_against_a_missing_arrow(power):
    assert pct(power[(0.2, 200)]) == pytest.approx(45, abs=8) and pct(power[(0.2, 500)]) == pytest.approx(94, abs=5) and power[(0.2, 2000)] > 0.99
    assert pct(power[(0.1, 500)]) == pytest.approx(31, abs=8) and pct(power[(0.1, 2000)]) == pytest.approx(93, abs=6)
    assert pct(power[(0.05, 2000)]) == pytest.approx(27, abs=8) and power[(0.05, 200)] < 0.1
    assert power[(0.5, 200)] > 0.99 and pct(power[(0.3, 200)]) == pytest.approx(87, abs=7)
