"""Auswertung: Aussagen eines Diagramms an Daten prüfen (Teilkorrelation, Fisher-z), die Experimente über feste Ströme und die Verdikte. Nur numpy."""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass

import numpy as np

import dsep_constants as C
import dsep_graph as G
from kausal_generator import Scm, SplitMix64, coefficient_matrix, sample

_ERFC = np.frompyfunc(math.erfc, 1, 1)


def de(x: float, digits: int = 2) -> str:
    """Zahl mit deutschem Dezimalkomma und typografischem Minuszeichen."""
    return f"{x:.{digits}f}".replace(".", ",").replace("-", "−")


def signed(x: float, digits: int = 2) -> str:
    return ("+" if x >= 0 else "−") + de(abs(x), digits)


# ----------------------------------------------------------------------------- Welten und Daten

def world_scm(world: str, coefs: dict | None = None) -> Scm:
    """Lineares Strukturmodell der Welt (Rauschen N(0,1) in jedem Knoten); `coefs` überschreibt die Koeffizienten (gleiche Kantenmenge)."""
    w = C.WORLDS[world]
    cf = dict(w["coefs"])
    if coefs:
        cf.update(coefs)
    n = len(w["nodes"])
    parents = G.parents_from_edges(n, cf)
    return Scm(
        names=w["nodes"],
        parents=parents,
        coefs=tuple(tuple(cf[(p, j)] for p in parents[j]) for j in range(n)),
        intercepts=(0.0,) * n,
        noise_sd=(1.0,) * n,
        binary=(False,) * n,
    )


def true_parents(world: str) -> tuple:
    return G.parents_from_edges(len(C.WORLDS[world]["nodes"]), C.WORLDS[world]["coefs"])


def population_cov(scm: Scm) -> np.ndarray:
    """Kovarianz im linearen Modell: Σ = (I − B)⁻¹ (I − B)⁻ᵀ bei Einheitsrauschen."""
    inv = np.linalg.inv(np.eye(len(scm.names)) - coefficient_matrix(scm))
    return inv @ inv.T


def sample_covariances(scm: Scm, n: int, rng: SplitMix64, reps: int = 1) -> np.ndarray:
    """Stichproben-Kovarianzen (reps, p, p) aus je n Beobachtungen."""
    d = sample(scm, n, rng, reps)
    data = np.stack([d[name] for name in scm.names], axis=1)               # (reps, p, n)
    data = data - data.mean(axis=2, keepdims=True)
    return np.einsum("rin,rjn->rij", data, data) / (n - 1)


def partial_correlations(cov: np.ndarray, x: int, y: int, z) -> np.ndarray:
    """Teilkorrelation von x und y gegeben z, je Kovarianzmatrix (Eingabe (p, p) oder (reps, p, p)); über die Präzisionsmatrix der Teilmatrix."""
    cov = np.asarray(cov)
    batch = cov if cov.ndim == 3 else cov[None]
    idx = [x, y] + list(z)
    prec = np.linalg.inv(batch[:, idx][:, :, idx])
    r = -prec[:, 0, 1] / np.sqrt(prec[:, 0, 0] * prec[:, 1, 1])
    return r if cov.ndim == 3 else r[0]


def fisher_p_values(r: np.ndarray, n: int, k: int) -> np.ndarray:
    """Zweiseitiger p-Wert des Fisher-z-Tests auf Teilkorrelation 0 bei n Beobachtungen und k bedingenden Größen."""
    zstat = np.arctanh(np.clip(np.asarray(r, dtype=float), -0.999999, 0.999999)) * math.sqrt(max(n - k - 3, 1))
    return np.asarray(_ERFC(np.abs(zstat) / math.sqrt(2.0)), dtype=float)


def test_statements(cov: np.ndarray, statements, n: int):
    """(r, p), je (reps, S): Teilkorrelation und p-Wert jeder Aussage (x, y, z) für jede Kovarianzmatrix."""
    batch = cov if cov.ndim == 3 else cov[None]
    cols_r, cols_p = [], []
    for x, y, z in statements:
        r = partial_correlations(batch, x, y, z)
        cols_r.append(r)
        cols_p.append(fisher_p_values(r, n, len(z)))
    if not statements:
        return np.zeros((len(batch), 0)), np.zeros((len(batch), 0))
    return np.stack(cols_r, axis=1), np.stack(cols_p, axis=1)


def family_rejected(p: np.ndarray, alpha: float = C.ALPHA, bonferroni: bool = False) -> np.ndarray:
    """Je Zeile: mindestens eine Aussage abgelehnt (roh zum Niveau alpha oder mit Bonferroni alpha / S)."""
    s = p.shape[1]
    if s == 0:
        return np.zeros(len(p), dtype=bool)
    return (p < (alpha / s if bonferroni else alpha)).any(axis=1)


# ----------------------------------------------------------------------------- Texte

def statement_text(names, statement) -> str:
    x, y, z = statement
    given = ", ".join(names[i] for i in z)
    return f"{names[x]} ⊥ {names[y]}" + (f" | {given}" if z else "")


def path_text(names, p: G.PathInfo) -> str:
    out = names[p.nodes[0]]
    for a, v in zip(p.arrows, p.nodes[1:]):
        out += f" {a} {names[v]}"
    return out


def path_reason(names, p: G.PathInfo) -> str:
    if not p.blocked:
        return "offen"
    if p.kind == "bedingt":
        return f"blockiert: {names[p.blocker]} ist vorgegeben"
    return f"blockiert: Collider {names[p.blocker]}, weder er noch ein Nachfahre ist vorgegeben"


# ----------------------------------------------------------------------------- Auswertung der Einstellungen

@dataclass(frozen=True)
class Settings:
    world: str = C.DEFAULT_WORLD
    edges: tuple = tuple(sorted(C.WORLDS[C.DEFAULT_WORLD]["coefs"]))
    x: int = 0
    y: int = 1
    z: tuple = ()
    scope: str = "basis"
    n: int = C.DEFAULT_N
    seed: int = C.DEFAULT_SEED


@dataclass
class StatementRow:
    statement: tuple
    text: str
    holds: bool          # gilt in der wahren Welt (d-getrennt im wahren Diagramm)
    r: float
    p: float
    reject_raw: bool
    reject_bonf: bool


@dataclass
class Analysis:
    settings: Settings
    names: tuple
    claimed: tuple
    truth: tuple
    separated: bool
    paths: list
    statements: list           # StatementRow
    n_basis: int
    n_cond2: int
    complete: bool
    missing: tuple             # wahre Kanten, die das gezeichnete Diagramm nicht hat
    extra: tuple               # Kanten des gezeichneten Diagramms, die in der Welt fehlen
    rejected_raw: int
    rejected_bonf: int


def analyse(s: Settings) -> Analysis:
    w = C.WORLDS[s.world]
    n_nodes = len(w["nodes"])
    claimed = G.parents_from_edges(n_nodes, s.edges)
    truth = true_parents(s.world)
    scm = world_scm(s.world)
    stmts = G.local_markov_basis(claimed) if s.scope == "basis" else G.separations(claimed, C.MAX_COND)
    cov = sample_covariances(scm, s.n, SplitMix64(s.seed))
    r, p = test_statements(cov, stmts, s.n)
    k = len(stmts)
    rows = [StatementRow(st, statement_text(w["nodes"], st), G.d_separated(truth, st[0], st[1], st[2]), float(r[0, i]), float(p[0, i]),
                         bool(p[0, i] < C.ALPHA), bool(p[0, i] < C.ALPHA / k)) for i, st in enumerate(stmts)]
    return Analysis(
        settings=s, names=w["nodes"], claimed=claimed, truth=truth,
        separated=G.d_separated(claimed, s.x, s.y, s.z), paths=G.explain_paths(claimed, s.x, s.y, s.z),
        statements=rows, n_basis=len(G.local_markov_basis(claimed)), n_cond2=len(G.separations(claimed, C.MAX_COND)), complete=G.is_complete(claimed),
        missing=tuple(sorted(set(G.edges_of(truth)) - set(G.edges_of(claimed)))), extra=tuple(sorted(set(G.edges_of(claimed)) - set(G.edges_of(truth)))),
        rejected_raw=sum(row.reject_raw for row in rows), rejected_bonf=sum(row.reject_bonf for row in rows),
    )


# ----------------------------------------------------------------------------- Experiment 1: Bedingen kann Zusammenhang erzeugen

def _collider_scm() -> Scm:
    return Scm(names=("A", "B", "C", "D"), parents=((), (), (0, 1), (2,)), coefs=((), (), (1.0, 1.0), (1.0,)), intercepts=(0.0,) * 4,
               noise_sd=(1.0, 1.0, 0.5, 0.5), binary=(False,) * 4)


def collider_experiment(n: int = C.EXP_COLLIDER_N) -> dict:
    """A und B unabhängig, C = A + B + 0,5ε, D = C + 0,5ε. Exakte Teilkorrelationen aus der Kovarianz; die Auswahl C > 0 per Simulation."""
    scm = _collider_scm()
    b = coefficient_matrix(scm)
    inv = np.linalg.inv(np.eye(4) - b)
    cov = inv @ np.diag(np.array(scm.noise_sd) ** 2) @ inv.T
    rows = [
        {"label": "ohne Bedingung", "value": float(partial_correlations(cov, 0, 1, ())), "kind": "exakt", "separated": True},
        {"label": "gegeben C (der Collider)", "value": float(partial_correlations(cov, 0, 1, (2,))), "kind": "exakt", "separated": False},
        {"label": "gegeben D (ein Nachfahre des Colliders)", "value": float(partial_correlations(cov, 0, 1, (3,))), "kind": "exakt", "separated": False},
    ]
    d = sample(scm, n, SplitMix64(C.SEED_BASE + 1))
    a_, b_, c_ = d["A"][0], d["B"][0], d["C"][0]
    sel = c_ > 0.0
    rows.append({"label": "bei Auswahl C > 0 (Selektion)", "value": float(np.corrcoef(a_[sel], b_[sel])[0, 1]), "kind": "simuliert, n = " + f"{n:,}".replace(",", "."),
                 "separated": False})
    return {"rows": rows, "n": n}


# ----------------------------------------------------------------------------- Experiment 2: Was das Diagramm behauptet

def six_variants() -> dict:
    """Wahres, um einen Pfeil ärmeres und um einen Pfeil reicheres Diagramm der 6-Knoten-Welt (Elterntupel)."""
    t = true_parents("6-Knoten-Beispiel")
    edges = set(G.edges_of(t))
    n = len(t)
    return {
        "wahres Diagramm": G.parents_from_edges(n, edges),
        "Pfeil Faktor → Servicegrad fehlt": G.parents_from_edges(n, edges - {C.MISSING_EDGE}),
        "Pfeil Region → Servicegrad überzählig": G.parents_from_edges(n, edges | {C.EXTRA_EDGE}),
    }


def statement_counts() -> list:
    """Aussagenzahlen je Welt: Basis, bis zwei Bedingungen, alle; vollständig?"""
    rows = []
    for name in C.WORLD_ORDER:
        par = true_parents(name)
        rows.append({"world": name, "nodes": len(par), "edges": len(G.edges_of(par)), "basis": len(G.local_markov_basis(par)),
                     "cond2": len(G.separations(par, C.MAX_COND)), "all": len(G.separations(par, None)), "complete": G.is_complete(par)})
    return rows


def claim_experiment(ns=C.EXP_CLAIM_NS, reps: int = C.EXP_CLAIM_REPS) -> list:
    """Wie oft wird ein Diagramm an der lokalen Basis abgelehnt (roh und mit Bonferroni): wahr, mit fehlendem und mit überzähligem Pfeil."""
    scm = world_scm("6-Knoten-Beispiel")
    variants = six_variants()
    rows = []
    for n in ns:
        cov = sample_covariances(scm, n, SplitMix64(C.SEED_BASE + 100 + n), reps)
        for name, par in variants.items():
            stm = G.local_markov_basis(par)
            _, p = test_statements(cov, stm, n)
            true_par = variants["wahres Diagramm"]
            rows.append({"variant": name, "n": n, "k": len(stm), "new": sum(1 for x, y, z in stm if not G.d_separated(true_par, x, y, z)),
                         "raw": float(family_rejected(p).mean()), "bonf": float(family_rejected(p, bonferroni=True).mean())})
    return rows


def equivalence_experiment() -> list:
    """Markov-Äquivalenzklassen aller DAGs auf 3 und 4 Knoten."""
    rows = []
    for n in (3, 4):
        classes = G.equivalence_classes(n)
        sizes = sorted(len(v) for v in classes.values())
        rows.append({"nodes": n, "dags": sum(sizes), "classes": len(classes), "singles": sum(1 for s in sizes if s == 1), "largest": max(sizes),
                     "complete": len(classes.get(frozenset(), []))})
    return rows


# ----------------------------------------------------------------------------- Experiment 3: Mehrfachtests am wahren Diagramm

def multitest_experiment(n: int = C.EXP_MULTI_N, reps: int = C.EXP_MULTI_REPS) -> list:
    scm = world_scm("6-Knoten-Beispiel")
    par = true_parents("6-Knoten-Beispiel")
    cov = sample_covariances(scm, n, SplitMix64(C.SEED_BASE + 300), reps)
    rows = []
    for label, stm in (("lokale Markov-Basis", G.local_markov_basis(par)), ("alle Aussagen mit höchstens zwei Bedingungen", G.separations(par, C.MAX_COND))):
        _, p = test_statements(cov, stm, n)
        k = len(stm)
        rows.append({"scope": label, "k": k, "raw": float(family_rejected(p).mean()), "bonf": float(family_rejected(p, bonferroni=True).mean()),
                     "naive": 1.0 - (1.0 - C.ALPHA) ** k})
    return rows


# ----------------------------------------------------------------------------- Experiment 4: Macht gegen einen fehlenden Pfeil

def power_experiment(coefs=C.EXP_POWER_COEFS, ns=C.EXP_POWER_NS, reps: int = C.EXP_POWER_REPS) -> list:
    """Das Diagramm ohne den Pfeil Faktor → Servicegrad wird geprüft; der Pfeil hat in der Welt den Koeffizienten c (Bonferroni an der lokalen Basis)."""
    claimed = six_variants()["Pfeil Faktor → Servicegrad fehlt"]
    stm = G.local_markov_basis(claimed)
    rows = []
    for ci, c in enumerate(coefs):
        scm = world_scm("6-Knoten-Beispiel", {C.MISSING_EDGE: c})
        for n in ns:
            cov = sample_covariances(scm, n, SplitMix64(C.SEED_BASE + 400 + 10 * ci + n), reps)
            _, p = test_statements(cov, stm, n)
            rows.append({"c": c, "n": n, "power": float(family_rejected(p, bonferroni=True).mean())})
    return rows


# ----------------------------------------------------------------------------- Verdikte: (Art, Text)

def verdict_query(a: Analysis) -> tuple[str, str]:
    s, names = a.settings, a.names
    pair = f"{names[s.x]} und {names[s.y]}"
    given = (" gegeben " + ", ".join(names[i] for i in s.z)) if s.z else " ohne Bedingung"
    open_paths = [p for p in a.paths if not p.blocked]
    if a.separated:
        return "success", f"{pair}{given}: **d-getrennt**. Alle {len(a.paths)} Pfade sind blockiert, das Diagramm behauptet Unabhängigkeit."
    return "info", f"{pair}{given}: **verbunden**. {len(open_paths)} von {len(a.paths)} Pfaden sind offen; das Diagramm behauptet keine Unabhängigkeit."


def verdict_check(a: Analysis) -> tuple[str, str]:
    k = len(a.statements)
    if k == 0:
        return "info", "Dieses Diagramm behauptet keine Unabhängigkeit: Jedes Paar ist durch einen Pfeil verbunden. Daten können es nicht widerlegen."
    if a.rejected_bonf:
        return "warning", (f"Das Diagramm wird abgelehnt: {a.rejected_bonf} von {k} Aussagen fallen auch mit Bonferroni durch. Mindestens ein fehlender Pfeil "
                           "spricht gegen die Daten (Niveau 5 %; eine Ablehnung kommt auch ohne Fehler im Diagramm gelegentlich vor).")
    if a.rejected_raw:
        return "info", (f"Roh werden {a.rejected_raw} von {k} Aussagen abgelehnt, mit Bonferroni keine: Bei {k} Tests ist das ohne jeden Fehler im Diagramm "
                        "häufig. Das Diagramm ist nicht abgelehnt, aber damit nicht bestätigt.")
    return "success", f"Keine der {k} Aussagen wird abgelehnt. Das Diagramm ist mit den Daten verträglich, aber nicht bestätigt: Andere Diagramme behaupten dasselbe."


def verdict_collider(res: dict) -> tuple[str, str]:
    rows = {r["label"]: r["value"] for r in res["rows"]}
    return "warning", (f"A und B sind unabhängig (Korrelation {de(rows['ohne Bedingung'], 2)}). Wer C vorgibt, findet {de(rows['gegeben C (der Collider)'], 2)}; "
                       f"wer einen Nachfahren vorgibt oder nur die Standorte mit C > 0 betrachtet, findet {de(rows['gegeben D (ein Nachfahre des Colliders)'], 2)} "
                       f"bzw. {de(rows['bei Auswahl C > 0 (Selektion)'], 2)}.")


def verdict_claim(rows: list) -> tuple[str, str]:
    at = {(r["variant"], r["n"]): r for r in rows}
    n = max(r["n"] for r in rows)
    return "info", (f"Bei n = {n} wird das Diagramm mit fehlendem Pfeil in {de(100 * at[('Pfeil Faktor → Servicegrad fehlt', n)]['bonf'], 0)} % der Stichproben "
                    f"abgelehnt (Bonferroni), das wahre in {de(100 * at[('wahres Diagramm', n)]['bonf'], 0)} %, das mit überzähligem Pfeil in "
                    f"{de(100 * at[('Pfeil Region → Servicegrad überzählig', n)]['bonf'], 0)} %. Ein überzähliger Pfeil behauptet weniger: Alle seine Aussagen sind wahr, er kann nicht widerlegt werden.")


def verdict_multitest(rows: list) -> tuple[str, str]:
    allr = rows[-1]
    return "warning", (f"Das wahre Diagramm wird bei {allr['k']} Aussagen roh in {de(100 * allr['raw'], 0)} % der Stichproben abgelehnt (naiv gerechnet "
                       f"{de(100 * allr['naive'], 0)} %, weil die Tests voneinander abhängen); mit Bonferroni in {de(100 * allr['bonf'], 1)} %.")


def verdict_power(rows: list) -> tuple[str, str]:
    at = {(r["c"], r["n"]): r["power"] for r in rows}
    return "info", (f"Ein fehlender Pfeil mit Koeffizient 0,2 wird bei n = 200 in {de(100 * at[(0.2, 200)], 0)} %, bei n = 500 in {de(100 * at[(0.2, 500)], 0)} % "
                    f"erkannt; mit Koeffizient 0,1 bei n = 500 nur in {de(100 * at[(0.1, 500)], 0)} %. Kleine Pfeile bleiben unsichtbar.")
