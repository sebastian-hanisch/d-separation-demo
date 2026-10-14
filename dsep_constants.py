"""Konstanten: Welten (wahre Diagramme mit Koeffizienten), Regler-Grenzen, Experimente, Farben und Presets."""

# Rechenaufwand am Maximum: eine Stichprobe mit n = 5 000 und 6 Knoten, Teilkorrelationen für höchstens 48 Aussagen, unter 50 ms.
N_MIN, N_MAX, N_STEP, DEFAULT_N = 100, 5000, 100, 500
SEED_MAX, DEFAULT_SEED = 999999, 35
ALPHA = 0.05
SCOPE_CHOICES = ("basis", "alle")
SCOPE_LABELS = {"basis": "Lokale Markov-Basis (wenige Aussagen)", "alle": "Alle Aussagen mit höchstens zwei Bedingungen"}
MAX_COND = 2

# Welten: Knoten in topologischer Reihenfolge (Pfeile gehen nur von kleinem zu großem Index), wahre Kanten mit Koeffizienten, Anordnung für die Zeichnung
# und die voreingestellte Frage (x, y, gegeben z). Die Daten kommen immer aus dem wahren Diagramm; das gezeichnete Diagramm kann davon abweichen.
WORLDS = {
    "Kette": {
        "nodes": ("Faktor", "Bestand", "Servicegrad"),
        "coefs": {(0, 1): 0.8, (1, 2): 0.8},
        "pos": ((0.0, 0.5), (0.5, 0.5), (1.0, 0.5)),
        "query": (0, 2, (1,)),
        "help": "Faktor → Bestand → Servicegrad: gibt man den Bestand vor, ist der Faktor für den Servicegrad ohne Belang.",
    },
    "Gabel": {
        "nodes": ("Schwankung", "Faktor", "Servicegrad"),
        "coefs": {(0, 1): 0.8, (0, 2): -0.7},
        "pos": ((0.5, 1.0), (0.0, 0.0), (1.0, 0.0)),
        "query": (1, 2, (0,)),
        "help": "Eine gemeinsame Ursache: Faktor und Servicegrad hängen zusammen, bis man die Schwankung vorgibt.",
    },
    "Collider": {
        "nodes": ("Region", "Wetter", "Lieferverzug"),
        "coefs": {(0, 2): 0.7, (1, 2): 0.7},
        "pos": ((0.0, 1.0), (1.0, 1.0), (0.5, 0.0)),
        "query": (0, 1, (2,)),
        "help": "Zwei unabhängige Ursachen eines Lieferverzugs: Wer den Lieferverzug festhält, erzeugt einen Zusammenhang zwischen Region und Wetter.",
    },
    "Collider mit Nachfahre": {
        "nodes": ("Region", "Wetter", "Lieferverzug", "Servicegrad"),
        "coefs": {(0, 2): 0.7, (1, 2): 0.7, (2, 3): -0.8},
        "pos": ((0.0, 1.0), (1.0, 1.0), (0.5, 0.5), (0.5, 0.0)),
        "query": (0, 1, (3,)),
        "help": "Auch ein Nachfahre des Colliders öffnet den Pfad: Region und Wetter hängen zusammen, wenn man den Servicegrad vorgibt.",
    },
    "Stück-1-Diagramm": {
        "nodes": ("Schwankung", "Faktor", "Servicegrad"),
        "coefs": {(0, 1): 0.8, (0, 2): -0.6, (1, 2): 0.5},
        "pos": ((0.5, 1.0), (0.0, 0.0), (1.0, 0.0)),
        "query": (1, 2, ()),
        "help": "Das Diagramm aus dem ersten Stück: alle drei Paare sind durch Pfeile verbunden, es behauptet keine Unabhängigkeit.",
    },
    "6-Knoten-Beispiel": {
        "nodes": ("Region", "Wetter", "Schwankung", "Faktor", "Lieferverzug", "Servicegrad"),
        "coefs": {(0, 2): 0.8, (2, 3): 0.9, (0, 4): 0.7, (1, 4): 0.7, (2, 5): -0.6, (3, 5): 0.5, (4, 5): -0.8},
        "pos": ((0.0, 0.5), (0.0, 0.0), (0.33, 0.75), (0.66, 0.9), (0.4, 0.15), (1.0, 0.4)),
        "query": (0, 1, ()),
        "help": "Kette, Gabel und Collider in einem Diagramm; die Standardfrage: sind Region und Wetter unabhängig?",
    },
}
WORLD_ORDER = tuple(WORLDS)
DEFAULT_WORLD = "6-Knoten-Beispiel"
SIX = WORLDS["6-Knoten-Beispiel"]
IDX = {name: i for i, name in enumerate(SIX["nodes"])}
# Fehlender und überzähliger Pfeil im 6-Knoten-Beispiel (Experimente)
MISSING_EDGE = (IDX["Faktor"], IDX["Servicegrad"])
EXTRA_EDGE = (IDX["Region"], IDX["Servicegrad"])

# Experimente: feste Ströme (Seeds aus SEED_BASE), nie ein einzelner Seed als Befund.
SEED_BASE = 800000
EXP_COLLIDER_N = 400_000
EXP_CLAIM_NS = (200, 500, 2000)
EXP_CLAIM_REPS = 300
EXP_MULTI_N, EXP_MULTI_REPS = 500, 500
EXP_POWER_COEFS = (0.05, 0.1, 0.2, 0.3, 0.5)
EXP_POWER_NS = (200, 500, 2000)
EXP_POWER_REPS = 200

COLOR_EDGE = "#6b6b6b"
COLOR_OPEN = "#D68A2E"
COLOR_NODE = "#2F6B65"
COLOR_COND = "#4c78a8"
COLOR_WARN = "#c0392b"
COLOR_MISSING = "#b0b0b0"


def preset(world: str, n: int = DEFAULT_N) -> dict:
    x, y, z = WORLDS[world]["query"]
    return {"world": world, "x": x, "y": y, "z": z, "scope": "basis", "n": n, "seed": DEFAULT_SEED}


PRESETS = {
    "6-Knoten-Beispiel (Voreinstellung)": preset("6-Knoten-Beispiel"),
    "Kette": preset("Kette"),
    "Gabel": preset("Gabel"),
    "Collider": preset("Collider"),
    "Collider mit Nachfahre": preset("Collider mit Nachfahre"),
    "Stück-1-Diagramm": preset("Stück-1-Diagramm"),
}
PRESET_HELP = {
    "6-Knoten-Beispiel (Voreinstellung)": WORLDS["6-Knoten-Beispiel"]["help"],
    "Kette": WORLDS["Kette"]["help"],
    "Gabel": WORLDS["Gabel"]["help"],
    "Collider": WORLDS["Collider"]["help"],
    "Collider mit Nachfahre": WORLDS["Collider mit Nachfahre"]["help"],
    "Stück-1-Diagramm": WORLDS["Stück-1-Diagramm"]["help"],
}
