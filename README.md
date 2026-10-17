# Das Diagramm lesen: d-Separation – Streamlit-Demo

**[→ Demo live ausprobieren](https://sebastianhanisch-d-separation-demo.streamlit.app/)**

Zweites Stück der Linie **Kausale Diagramme und Adjustierung** in der „Konzepte“-Reihe im Portfolio von [Sebastian Hanisch](https://sebastianhanisch.net) (Operations Research und Machine Learning). Nachfolger von [konfundierung-demo](https://github.com/sebastian-hanisch/konfundierung-demo): Dort zeigten zwei verschiedene Ursachen-Diagramme dieselben Daten. Hier steht, **was** ein Diagramm über die Daten behauptet, und wie man es liest.

## Kernfrage

Ein Diagramm behauptet nur, was es weglässt: Jeder fehlende Pfeil ist eine Unabhängigkeit, die sich an Daten prüfen lässt. Wie liest man diese Aussagen aus dem Diagramm, wann öffnet Bedingen einen Pfad, wie oft lehnen Daten ein richtiges Diagramm ab, und welche Fehler im Diagramm bleiben unsichtbar?

## Modell

- **Diagramm:** gerichteter azyklischer Graph in fester topologischer Reihenfolge (Pfeile nur von kleinem zu großem Index, also nie ein Zyklus), je Welt 3 bis 6 Knoten.
- **Welten:** Kette, Gabel, Collider, Collider mit Nachfahre, das Diagramm aus dem ersten Stück (vollständig) und ein 6-Knoten-Beispiel (Region, Wetter, Schwankung, Faktor, Lieferverzug, Servicegrad; 7 Pfeile).
- **Daten:** lineares Normalmodell mit Einheitsrauschen aus dem wahren Diagramm der Welt (Generator `kausal_generator.py`, wortgleich in allen Stücken der Linie). Das gezeichnete Diagramm darf davon abweichen.
- **Aussagen:** jede d-Separation (x, y, gegeben Z) behauptet Teilkorrelation 0. Geprüft werden entweder die lokale Markov-Basis (12 im Beispiel) oder alle mit höchstens zwei Bedingungen (29).

## Methodik

- **d-Separation** über die Moralisierung des Vorfahren-Graphen (Lauritzen u. a. 1990). Die Pfade mit Blockierungsgrund (Kette oder Gabel mit Zielknoten in Z, Collider ohne Nachfahren in Z) sind der zweite Rechenweg und die Erklärung in der App.
- **Test:** Teilkorrelation über die Präzisionsmatrix der Stichproben-Kovarianz, Fisher-z-p-Wert; roh zum 5-%-Niveau je Aussage und mit Bonferroni (Holm lehnt „mindestens eine“ genau dann ab wie Bonferroni und fehlt deshalb).
- **Experimente** laufen über feste Zufallsströme (SplitMix64): 300 bis 500 Wiederholungen je Zelle, nie ein einzelner Seed.

## Befunde (gemessen, keine Behauptungen)

Alle Zahlen stehen in `tests/test_claims.py`. „Basis“ ist die lokale Markov-Basis des Diagramms.

| Frage | Befund | Test |
|---|---|---|
| Wie viele Aussagen hat das 6-Knoten-Beispiel? | **12** in der lokalen Basis, 29 mit höchstens zwei Bedingungen, 48 insgesamt (7 Pfeile, 15 Paare). | `test_six_node_example_has_twelve_basis_statements_29_with_two_conditions_and_48_in_total` |
| Aussagen je Welt | Kette, Gabel, Collider je 1; Collider mit Nachfahre 5; das Diagramm aus Stück 1 **0**. | `test_statement_counts_by_world` |
| Wie viele Diagramme sind aus Daten nicht zu unterscheiden? | 25 Diagramme auf 3 Knoten in **11** Klassen (4 allein in ihrer Klasse, größte Klasse 6), 543 Diagramme auf 4 Knoten in **185** Klassen (59 allein, größte 24). | `test_all_twenty_five_and_543_diagrams_fall_into_11_and_185_classes` |
| Collider (A, B unabhängig, C = A + B + 0,5ε, D = C + 0,5ε) | Korrelation von A und B: 0; gegeben C **−0,80**; gegeben den Nachfahren D −0,67; bei Auswahl C > 0 (simuliert) −0,39. | `test_experiment_1_collider_partial_correlations` |
| Collider im 6-Knoten-Beispiel | Region und Wetter: gegeben Lieferverzug −0,33, gegeben Servicegrad (Nachfahre) −0,17, ohne Bedingung 0. | `test_the_collider_in_the_six_node_world_gives_the_numbers_of_the_assumptions_text` |
| Standard-Stichprobe (n = 500, Seed 35) | 1 von 12 Aussagen roh abgelehnt, mit Bonferroni keine; Region und Wetter sind d-getrennt (3 blockierte Pfade). | `test_default_sample_rejects_one_of_twelve_raw_and_none_with_bonferroni` |
| Wird ein Diagramm mit fehlendem Pfeil abgelehnt? | Ja: Pfeil Faktor → Servicegrad (Koeffizient 0,5) fehlt: in **100 %** der Stichproben bei n = 200, 500, 2 000, roh und mit Bonferroni; 4 der 14 Basisaussagen gelten in der Welt nicht. | `test_experiment_2_missing_arrow_is_always_rejected` |
| Und ein überzähliger Pfeil? | **Nicht häufiger als das wahre Diagramm:** mit Bonferroni 4 bis 6 % (wahr: 3 bis 6 %); roh rund 33 bis 42 % (wahr: 37 bis 46 %). Er behauptet weniger und ist nicht prüfbar. | `test_experiment_2_true_and_extra_arrow_diagrams_are_rejected_about_equally_often` |
| Wie oft lehnt ein Test das wahre Diagramm ab? | Roh bei n = 500: **40 %** (12 Aussagen) bzw. **47 %** (29); naiv gerechnet 46 % bzw. 77 %, weil die Tests voneinander abhängen. Mit Bonferroni 2 bis 3 %. | `test_experiment_3_family_wise_rejection_of_the_true_diagram` |
| Wie groß muss ein fehlender Pfeil sein? | Koeffizient 0,2: erkannt in rund 45 % (n = 200), 94 % (n = 500), 100 % (n = 2 000); Koeffizient 0,1: rund 30 % bei n = 500, 93 % bei n = 2 000; Koeffizient 0,05: rund 27 % bei n = 2 000 (200 Wiederholungen je Zelle, Fehler etwa ±3 Punkte). | `test_experiment_4_power_against_a_missing_arrow` |

## Ehrliche Grenzen

| Annahme | Was passiert, wenn sie verletzt ist | Wer setzt an |
|---|---|---|
| **Linear und normalverteilt** | Der Test prüft lineare Teilkorrelation; nichtlineare Abhängigkeit ohne Korrelation bleibt unsichtbar. | – |
| **Alle Größen sind beobachtet** | Eine unbeobachtete gemeinsame Ursache steht nicht im Diagramm. | Sensitivität und Falsifikation |
| **Ein Test je Aussage** | Bei 29 Aussagen wird das wahre Diagramm roh in 47 % der Stichproben abgelehnt. | – |
| **Ablehnen heißt falsch, Nichtablehnen heißt richtig** | Ein überzähliger Pfeil wird nicht häufiger abgelehnt; 25 Diagramme auf 3 Knoten ergeben nur 11 Aussagenklassen. | Wie falsch darf das Diagramm sein? |
| **Die Daten bestimmen das Diagramm** | Diagramme derselben Klasse sind nicht zu trennen. | Das Diagramm aus Daten lernen |
| **Die Aussagen legen die Pfeilrichtungen fest** | Nur ein Collider legt sie fest; eine Kette, eine Gabel und die umgekehrte Kette bilden eine Klasse. | Das Diagramm aus Daten lernen |

Die Zahlen gelten für diese erfundene Welt; „Wahrheit“ ist das simulierte Modell, nicht ein Befund über echte Standorte.

## Bezug zu den Nachbarn im Portfolio

- [konfundierung-demo](https://github.com/sebastian-hanisch/konfundierung-demo): zeigt zwei Diagramme mit derselben Verteilung; die Erklärung (beide vollständig, 0 Aussagen) steht hier.
- [multiple-testing-demo](https://github.com/sebastian-hanisch/multiple-testing-demo): Mehrfachtests und Gewinnerfluch; hier nur als Hinweis auf die 40 bis 47 %.
- Die Moralisierung nutzt dieselbe Breitensuche wie die Linie *Graphen und Netzwerke*, auf dem moralisierten Graphen.

## Tests

Mini-Instanz von Hand, drei Rechenwege der d-Separation (Moralisierung, Pfadblockierung, `networkx.is_d_separator`) auf allen Diagrammen mit 3 und 4 Knoten und 250 Zufallsdiagrammen, Teilkorrelation gegen Regressionsresiduen, Population (d-getrennt = Teilkorrelation 0), Gegenprobe mit Treue-Verletzung, Generator (SplitMix64 gegen eine unabhängige Fassung), Auswertung, jede README-Zahl in `test_claims.py`, AppTest (Presets, Welt-Wechsel, Pfeile, Bedingungsmenge, Permalink, PDF), Footer und Laufzeit-Importe.

```bash
python -m pytest tests -q
```

## Dateistruktur

| Datei | Inhalt |
|---|---|
| `app.py` | Streamlit-Oberfläche |
| `kausal_generator.py` | gemeinsamer Generator der Linie (SplitMix64, Strukturmodell) |
| `dsep_graph.py` | Elternmengen, d-Separation, Pfade, Aussagenmengen, Äquivalenzklassen |
| `dsep_evaluation.py` | Teilkorrelation, Fisher-z, Analyse, Experimente, Verdikte |
| `dsep_visualization.py`, `dsep_pdf_export.py` | Figuren, Tabellen, PDF |
| `dsep_constants.py`, `dsep_presets.py` | Welten, Regler, Presets, Permalink, Zustandsbereinigung |
| `tests/` | Mini-Instanz, Orakel, Claims, App |

## Bewusst nicht umgesetzt

- **Aus Daten das Diagramm lernen** (PC, NOTEARS): eigene Stücke der Linie; hier wird nur die Äquivalenzklasse gezählt.
- **Adjustierung:** welche Variablen man festhalten darf, um eine Wirkung zu schätzen, ist das nächste Stück; hier nur, was ein Diagramm behauptet.
- **Nichtlineare und nicht normalverteilte Modelle, unbeobachtete Variablen, Zeitreihen:** nicht gebaut; alle Zahlen sind erzeugt.

## Lokal ausführen

```bash
pip install -r requirements.txt
streamlit run app.py
```

Streamlit Cloud: Python 3.12.

Gebaut mit Streamlit, Plotly, numpy, pandas und fpdf2.

Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). Mehr zur Reihe: [Kausale Diagramme: von Konfundierung bis Wahl](https://sebastianhanisch.net/konzepte-kausale-diagramme.html).
