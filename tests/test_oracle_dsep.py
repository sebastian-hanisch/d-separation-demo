"""Orakel: Kernroutinen gegen einen unabhängigen Rechenweg (networkx, numpy, scipy). Unter zehn Sekunden; ohne die Pakete überspringt sich die Datei."""

import itertools
import math

import numpy as np
import pytest

nx = pytest.importorskip("networkx")
scipy_stats = pytest.importorskip("scipy.stats")

import dsep_constants as C  # noqa: E402
import dsep_evaluation as ev  # noqa: E402
import dsep_graph as G  # noqa: E402
from kausal_generator import SplitMix64  # noqa: E402


def to_nx(parents):
    g = nx.DiGraph()
    g.add_nodes_from(range(len(parents)))
    g.add_edges_from((p, c) for c, ps in enumerate(parents) for p in ps)
    return g


def random_dag(n, p, rng):
    return tuple(tuple(i for i in range(j) if rng.random() < p) for j in range(n))


def test_d_separation_against_networkx_on_every_dag_with_three_and_four_nodes():
    for n in (3, 4):
        for parents in G.all_dags(n):
            g = to_nx(parents)
            for x, y in itertools.combinations(range(n), 2):
                rest = [v for v in range(n) if v not in (x, y)]
                for k in range(len(rest) + 1):
                    for z in itertools.combinations(rest, k):
                        assert G.d_separated(parents, x, y, z) == nx.is_d_separator(g, {x}, {y}, set(z)), (parents, x, y, z)


def test_d_separation_against_networkx_and_the_path_definition_on_random_dags():
    rng = np.random.default_rng(1)
    for _ in range(250):
        n = int(rng.integers(5, 8))
        parents = random_dag(n, float(rng.uniform(0.2, 0.6)), rng)
        g = to_nx(parents)
        for _ in range(12):
            x, y = (int(v) for v in rng.choice(n, 2, replace=False))
            z = [v for v in range(n) if v not in (x, y) and rng.random() < 0.4]
            sep = G.d_separated(parents, x, y, z)
            assert sep == nx.is_d_separator(g, {x}, {y}, set(z))
            assert sep == all(p.blocked for p in G.explain_paths(parents, x, y, z))


def test_ancestors_and_descendants_against_networkx():
    rng = np.random.default_rng(2)
    for _ in range(100):
        n = int(rng.integers(4, 8))
        parents = random_dag(n, 0.4, rng)
        g = to_nx(parents)
        for v in range(n):
            assert G.descendants(parents, v) == nx.descendants(g, v)
            assert G.ancestors(parents, {v}) == nx.ancestors(g, v) | {v}


def test_local_markov_basis_against_networkx_definition_and_implied_by_all_statements():
    rng = np.random.default_rng(3)
    for _ in range(60):
        n = int(rng.integers(3, 7))
        parents = random_dag(n, 0.4, rng)
        g = to_nx(parents)
        expected = set()
        for v in range(n):
            others = set(range(n)) - {v} - nx.descendants(g, v) - set(parents[v])
            for u in others:
                expected.add((min(u, v), max(u, v), tuple(sorted(parents[v]))))
        assert set(G.local_markov_basis(parents)) == expected
        assert expected <= set(G.separations(parents, None))


def test_population_partial_correlations_vanish_exactly_for_separations_and_not_for_connections():
    """Lineares Normalmodell mit zufälligen Koeffizienten: d-getrennt gleich Teilkorrelation 0; verbunden ungleich 0 (generische Koeffizienten)."""
    rng = np.random.default_rng(4)
    checked = 0
    for _ in range(40):
        n = int(rng.integers(4, 7))
        parents = random_dag(n, 0.45, rng)
        b = np.zeros((n, n))
        for c, ps in enumerate(parents):
            for p in ps:
                b[c, p] = rng.choice([-1.0, 1.0]) * rng.uniform(0.4, 1.2)
        inv = np.linalg.inv(np.eye(n) - b)
        cov = inv @ inv.T
        for x, y in itertools.combinations(range(n), 2):
            rest = [v for v in range(n) if v not in (x, y)]
            for k in range(min(3, len(rest)) + 1):
                for z in itertools.combinations(rest, k):
                    r = float(ev.partial_correlations(cov, x, y, z))
                    if G.d_separated(parents, x, y, z):
                        assert abs(r) < 1e-9
                        checked += 1
                    else:
                        assert abs(r) > 1e-6
    assert checked > 300


def test_a_faithfulness_violation_can_make_a_connected_pair_look_separated():
    """Gegenprobe: A -> B -> C und A -> C mit direktem Effekt, der den Umweg genau aufhebt (1·1 + (−1) = 0): A, C sind d-verbunden, die Kovarianz ist 0."""
    parents = ((), (0,), (0, 1))
    b = np.zeros((3, 3))
    b[1, 0], b[2, 1], b[2, 0] = 1.0, 1.0, -1.0
    inv = np.linalg.inv(np.eye(3) - b)
    cov = inv @ inv.T
    assert not G.d_separated(parents, 0, 2, ())
    assert abs(cov[0, 2]) < 1e-12


def test_partial_correlation_against_the_residual_correlation_of_two_regressions():
    scm = ev.world_scm("6-Knoten-Beispiel")
    cov = ev.population_cov(scm)
    rng = np.random.default_rng(5)
    x = rng.multivariate_normal(np.zeros(6), cov, size=4000)
    for (i, j, z) in [(0, 1, (4,)), (2, 5, (3, 4)), (3, 5, (2,)), (0, 5, ())]:
        design = np.column_stack([np.ones(len(x))] + [x[:, v] for v in z])
        ri = x[:, i] - design @ np.linalg.lstsq(design, x[:, i], rcond=None)[0]
        rj = x[:, j] - design @ np.linalg.lstsq(design, x[:, j], rcond=None)[0]
        sample_r = float(np.corrcoef(ri, rj)[0, 1])
        assert sample_r == pytest.approx(float(ev.partial_correlations(np.cov(x, rowvar=False), i, j, z)), abs=1e-9)
        assert sample_r == pytest.approx(float(ev.partial_correlations(cov, i, j, z)), abs=0.06)


@pytest.mark.parametrize("r,n,k", [(0.0, 100, 0), (0.1, 500, 2), (-0.25, 200, 1), (0.6, 50, 3), (0.05, 5000, 0)])
def test_fisher_p_value_against_scipy(r, n, k):
    z = math.atanh(r) * math.sqrt(n - k - 3)
    assert float(ev.fisher_p_values(np.array([r]), n, k)[0]) == pytest.approx(2 * float(scipy_stats.norm.sf(abs(z))), rel=1e-9, abs=1e-12)


def test_wrong_diagrams_are_rejected_and_true_ones_roughly_at_the_nominal_rate():
    scm = ev.world_scm("6-Knoten-Beispiel")
    variants = ev.six_variants()
    cov = ev.sample_covariances(scm, 500, SplitMix64(11), reps=200)
    rates = {}
    for name, par in variants.items():
        _, p = ev.test_statements(cov, G.local_markov_basis(par), 500)
        rates[name] = float(ev.family_rejected(p, bonferroni=True).mean())
    assert rates["Pfeil Faktor → Servicegrad fehlt"] > 0.95
    assert rates["wahres Diagramm"] < 0.15 and rates["Pfeil Region → Servicegrad überzählig"] < 0.15


def test_true_statements_hold_in_the_true_world_by_the_analysis():
    a = ev.analyse(ev.Settings(world="6-Knoten-Beispiel", edges=tuple(sorted(C.WORLDS["6-Knoten-Beispiel"]["coefs"])), scope="alle"))
    assert all(row.holds for row in a.statements) and len(a.statements) == 29
