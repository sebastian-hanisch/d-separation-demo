"""PDF-Export der aktuellen Prüfung (fpdf2). Kernschriften sind latin-1: Umlaute gehen, Pfeile und Sonderzeichen werden ersetzt."""

from __future__ import annotations

from fpdf import FPDF

import dsep_constants as C
from dsep_evaluation import Analysis, de, path_reason, path_text

_REPLACE = {"→": "->", "←": "<-", "⊥": "_|_", "–": "-", "—": "-", "−": "-", "€": "EUR", "≥": ">=", "≤": "<="}
MAX_ROWS = 40


def _s(text) -> str:
    out = str(text)
    for old, new in _REPLACE.items():
        out = out.replace(old, new)
    return out.encode("latin-1", "replace").decode("latin-1")


def build_pdf(a: Analysis) -> bytes:
    s = a.settings
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(0, 9, _s("Das Diagramm lesen: d-Separation"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    given = ", ".join(a.names[i] for i in s.z) or "nichts"
    pdf.multi_cell(0, 5, _s(f"Welt: {s.world}. Frage: {a.names[s.x]} und {a.names[s.y]}, gegeben {given}. Beobachtungen n = {s.n}, Seed {s.seed}. Alles simuliert."),
                   new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    lines = [
        f"Ergebnis: {'d-getrennt' if a.separated else 'verbunden'}; {sum(1 for p in a.paths if not p.blocked)} von {len(a.paths)} Pfaden offen.",
        f"Aussagen: lokale Basis {a.n_basis}, bis zwei Bedingungen {a.n_cond2}; geprueft: {len(a.statements)}.",
        f"Abgelehnt: roh {a.rejected_raw}, mit Bonferroni {a.rejected_bonf}.",
    ]
    for line in lines:
        pdf.multi_cell(0, 5, _s(line), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 6, _s("Pfade"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    for p in a.paths[:MAX_ROWS]:
        pdf.multi_cell(0, 5, _s(f"{path_text(a.names, p)}: {path_reason(a.names, p)}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 9)
    for h, w in zip(["Aussage", "gilt", "r", "p", "roh", "Bonf."], [92, 14, 20, 20, 16, 18]):
        pdf.cell(w, 6, _s(h), border=1)
    pdf.ln()
    pdf.set_font("Helvetica", "", 8)
    for row in a.statements[:MAX_ROWS]:
        vals = [row.text, "ja" if row.holds else "nein", de(row.r, 3), de(row.p, 3), "ja" if row.reject_raw else "-", "ja" if row.reject_bonf else "-"]
        for v, w in zip(vals, [92, 14, 20, 20, 16, 18]):
            pdf.cell(w, 5.5, _s(v)[:60], border=1)
        pdf.ln()
    if len(a.statements) > MAX_ROWS:
        pdf.cell(0, 5, _s(f"... {len(a.statements) - MAX_ROWS} weitere Aussagen nicht gezeigt."), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 8)
    pdf.multi_cell(0, 4, _s(f"Test: Fisher-z auf Teilkorrelation, Niveau {C.ALPHA:g}. Quelle: d-separation-demo, Sebastian Hanisch."), new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())
