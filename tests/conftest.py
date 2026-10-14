"""Gemeinsame Fixtures: die Mini-Instanz, an der jede Einheit von Hand geprüft wird (DEMO-PLAYBOOK §1b)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def mini():
    """4 Knoten A, B, C, D mit A -> C <- B und C -> D (Elterntupel). Handrechnung:
    d-Separationen mit beliebiger Bedingungsmenge: A ⊥ B; A ⊥ D | C; A ⊥ D | B, C; B ⊥ D | C; B ⊥ D | A, C (5 Aussagen).
    Nicht getrennt: A, B gegeben C oder D (Collider und Nachfahre öffnen); A, D gegeben nur B (A -> C -> D bleibt offen).
    Lokale Markov-Basis: A ⊥ B; A ⊥ D | C; B ⊥ D | C."""
    return ((), (), (0, 1), (2,))


A, B, C, D = 0, 1, 2, 3
