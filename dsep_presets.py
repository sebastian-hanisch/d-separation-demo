"""Permalink (Begrenzen), Presets, Zustandsbereinigung und Zufalls-Seed-Button (Standardmuster aus dem Demo-Portfolio).

Alle Regler sind in jeder Einstellung wirksam und werden immer gezeichnet. Berechnete Auswahllisten (Pfeile, Knoten) hängen von der Welt ab; deshalb
bereinigt `clean_state` vor dem Zeichnen jeden Wert, der in der aktuellen Welt nicht vorkommt.
"""

import random

import streamlit as st

import dsep_constants as C

STATE_KEYS = ("world_select", "edges_select", "x_select", "y_select", "z_select", "scope_select", "n_slider", "seed_input")


def edge_key(i: int, j: int) -> str:
    return f"{i}-{j}"


def parse_edge(key: str) -> tuple:
    a, b = key.split("-")
    return int(a), int(b)


def n_nodes(world: str) -> int:
    return len(C.WORLDS[world]["nodes"])


def true_edge_keys(world: str) -> list:
    return [edge_key(i, j) for (i, j) in sorted(C.WORLDS[world]["coefs"])]


def all_edge_keys(world: str) -> list:
    n = n_nodes(world)
    return [edge_key(i, j) for i in range(n) for j in range(i + 1, n)]


def init_session_state_defaults():
    base = C.PRESETS["6-Knoten-Beispiel (Voreinstellung)"]
    defaults = {"world_select": base["world"], "edges_select": true_edge_keys(base["world"]), "x_select": base["x"], "y_select": base["y"],
                "z_select": list(base["z"]), "scope_select": base["scope"], "n_slider": base["n"], "seed_input": base["seed"]}
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def bounds(key):
    return {"n_slider": (C.N_MIN, C.N_MAX), "seed_input": (0, C.SEED_MAX)}[key]


def clean_state():
    """Vor dem Zeichnen der Regler: nur Werte behalten, die in der aktuellen Welt gültig sind (Welt, Pfeile, Knoten, Bedingungsmenge)."""
    ss = st.session_state
    if ss.get("world_select") not in C.WORLDS:
        ss["world_select"] = C.DEFAULT_WORLD
    world = ss["world_select"]
    n = n_nodes(world)
    valid = set(all_edge_keys(world))
    ss["edges_select"] = [k for k in ss.get("edges_select", []) if k in valid]
    x = ss.get("x_select", 0)
    y = ss.get("y_select", 1)
    x = x if isinstance(x, int) and 0 <= x < n else 0
    y = y if isinstance(y, int) and 0 <= y < n and y != x else next(v for v in range(n) if v != x)
    ss["x_select"], ss["y_select"] = x, y
    ss["z_select"] = [v for v in ss.get("z_select", []) if isinstance(v, int) and 0 <= v < n and v not in (x, y)]
    if ss.get("scope_select") not in C.SCOPE_CHOICES:
        ss["scope_select"] = "basis"
    ss["n_slider"] = min(C.N_MAX, max(C.N_MIN, int(ss.get("n_slider", C.DEFAULT_N))))


def load_permalink_settings():
    """Einmal je Sitzung: Werte aus der Adresszeile übernehmen; ungültige Werte werden von `clean_state` bereinigt."""
    if "permalink_loaded" in st.session_state:
        return
    qp = st.query_params
    init_session_state_defaults()
    ss = st.session_state
    if "w" in qp and qp["w"] in C.WORLDS:
        ss["world_select"] = qp["w"]
        ss["edges_select"] = true_edge_keys(qp["w"])
        x, y, z = C.WORLDS[qp["w"]]["query"]
        ss["x_select"], ss["y_select"], ss["z_select"] = x, y, list(z)

    def ints(text):
        return [int(t) for t in text.split(",") if t.strip().lstrip("-").isdigit()]

    try:
        if "e" in qp:
            ss["edges_select"] = [t for t in qp["e"].split(",") if t.count("-") == 1 and all(p.isdigit() for p in t.split("-"))]
        if "x" in qp:
            ss["x_select"] = int(qp["x"])
        if "y" in qp:
            ss["y_select"] = int(qp["y"])
        if "z" in qp:
            ss["z_select"] = ints(qp["z"])
        if "sc" in qp and qp["sc"] in C.SCOPE_CHOICES:
            ss["scope_select"] = qp["sc"]
        if "n" in qp:
            ss["n_slider"] = int(qp["n"])
        if "seed" in qp:
            ss["seed_input"] = max(0, min(C.SEED_MAX, int(qp["seed"])))
    except (ValueError, TypeError):
        pass
    ss["permalink_loaded"] = True


def sync_query_params(values: dict):
    """`values`: Parameter -> Text; die Adresszeile spiegelt die Konfiguration."""
    try:
        for key, value in values.items():
            st.query_params[key] = str(value)
    except Exception:
        pass


def apply_preset(name):
    p = C.PRESETS[name]
    st.session_state["world_select"] = p["world"]
    st.session_state["edges_select"] = true_edge_keys(p["world"])
    st.session_state["x_select"], st.session_state["y_select"], st.session_state["z_select"] = p["x"], p["y"], list(p["z"])
    st.session_state["scope_select"] = p["scope"]
    st.session_state["n_slider"] = p["n"]
    st.session_state["seed_input"] = p["seed"]


def on_world_change():
    """Neue Welt: gezeichnetes Diagramm = wahres Diagramm, Frage = Voreinstellung der Welt."""
    world = st.session_state["world_select"]
    st.session_state["edges_select"] = true_edge_keys(world)
    x, y, z = C.WORLDS[world]["query"]
    st.session_state["x_select"], st.session_state["y_select"], st.session_state["z_select"] = x, y, list(z)


def reset_edges():
    st.session_state["edges_select"] = true_edge_keys(st.session_state["world_select"])


def randomize_seed():
    st.session_state["seed_input"] = random.randint(0, C.SEED_MAX)


def claimed_edges() -> tuple:
    return tuple(sorted(parse_edge(k) for k in st.session_state.get("edges_select", [])))


def edges_text(edges) -> str:
    return ",".join(edge_key(i, j) for i, j in edges)
