"""Das Diagramm lesen: d-Separation - interaktive Konzept-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Zweites Stück der Linie Kausale Diagramme und Adjustierung. Ein gezeichnetes Diagramm behauptet Unabhängigkeiten; die Demo liest sie mit der d-Separation
aus und prüft sie an Daten aus einem simulierten wahren Diagramm. Kern: dsep_graph.py, Generator: kausal_generator.py (wortgleich in allen Repos der Linie).

Lauffähig mit: streamlit run app.py
"""

import streamlit as st

import dsep_constants as C
from dsep_evaluation import (
    Settings,
    analyse,
    claim_experiment,
    collider_experiment,
    de,
    equivalence_experiment,
    multitest_experiment,
    power_experiment,
    statement_counts,
    statement_text,
    verdict_check,
    verdict_claim,
    verdict_collider,
    verdict_multitest,
    verdict_power,
    verdict_query,
)
from dsep_graph import separations
from dsep_pdf_export import build_pdf
from dsep_presets import (
    all_edge_keys,
    apply_preset,
    bounds,
    claimed_edges,
    clean_state,
    edges_text,
    init_session_state_defaults,
    load_permalink_settings,
    n_nodes,
    on_world_change,
    parse_edge,
    randomize_seed,
    reset_edges,
    sync_query_params,
)
from dsep_visualization import (
    build_claim,
    build_collider,
    build_diagram,
    build_paths_table,
    build_power,
    build_statements_table,
    style_statements,
)

st.set_page_config(page_title="d-Separation – Sebastian Hanisch", layout="wide")

SPINNER = "Experiment rechnet über feste Zufallsströme …"


@st.cache_data(show_spinner=False)
def _analysis(settings):
    return analyse(settings)


@st.cache_data(show_spinner=SPINNER)
def _collider():
    return collider_experiment()


@st.cache_data(show_spinner=SPINNER)
def _claim():
    return claim_experiment()


@st.cache_data(show_spinner=SPINNER)
def _equivalence():
    return equivalence_experiment()


@st.cache_data(show_spinner=SPINNER)
def _multitest():
    return multitest_experiment()


@st.cache_data(show_spinner=SPINNER)
def _power():
    return power_experiment()


@st.cache_data(show_spinner=False)
def _counts():
    return statement_counts()


def verdict(kind_text):
    kind, text = kind_text
    getattr(st, kind)(text)


st.title("🔍 Das Diagramm lesen: d-Separation")
st.markdown(
    """
**Ein Diagramm behauptet nur, was es weglässt.** Dies ist das zweite Stück der Linie **Kausale Diagramme und Adjustierung**. Das erste Stück hat gezeigt, dass zwei
verschiedene Ursachen-Diagramme dieselben Daten erzeugen können. Hier steht, **was** ein Diagramm über die Daten behauptet: Jeder fehlende Pfeil ist eine
Unabhängigkeit, und die **d-Separation** liest diese Unabhängigkeiten aus dem Diagramm. Die Demo zeichnet ein Diagramm, nennt seine Aussagen und prüft sie an Daten aus
einem simulierten wahren Diagramm.

Weiter unten: vier Experimente (**🔬**), **🚧 Wo die Annahmen enden** und der Expander **📐 Mathematische Formulierung**.
"""
)

with st.expander("So funktioniert d-Separation", expanded=True):
    st.markdown(
        """
1. **Pfade.** Ein Pfad verbindet zwei Knoten über beliebig gerichtete Pfeile. Nur Pfade zwischen den beiden Knoten der Frage zählen.
2. **Drei Bausteine.** *Kette* (A → M → B) und *Gabel* (A ← M → B) sind offen, bis man M vorgibt; dann sind sie blockiert. Ein *Collider* (A → C ← B) ist umgekehrt
   **blockiert**, bis man C **oder einen Nachfahren von C** vorgibt; dann öffnet er den Pfad.
3. **d-getrennt.** Sind alle Pfade zwischen x und y blockiert, behauptet das Diagramm: x und y sind unabhängig, gegeben die Bedingungsmenge.
4. **Wozu das gut ist.** Diese Aussagen kann man an Daten prüfen und widerlegen. Die Pfeile selbst sieht man nicht, und ein Diagramm ohne fehlenden Pfeil behauptet nichts.
        """
    )

st.caption("🎯 Schnellstart – ein Beispielszenario laden:")
cols = st.columns(len(C.PRESETS))
for col, name in zip(cols, C.PRESETS):
    with col:
        st.button(name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP.get(name, ""), key=f"preset_{name}")

st.caption("🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, um ein Szenario zu teilen.")

load_permalink_settings()
init_session_state_defaults()
clean_state()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    st.markdown("**Welt (liefert die Daten)**")
    world = st.selectbox("Wahres Diagramm", C.WORLD_ORDER, key="world_select", on_change=on_world_change,
                         help="Aus diesem Diagramm stammen die Daten. Wechselt man die Welt, wird das gezeichnete Diagramm zurückgesetzt.")
    nn = n_nodes(world)
    names = C.WORLDS[world]["nodes"]
    st.markdown("**Gezeichnetes Diagramm**")
    st.multiselect("Pfeile", all_edge_keys(world), key="edges_select", format_func=lambda k: f"{names[parse_edge(k)[0]]} → {names[parse_edge(k)[1]]}",
                   help="Welche Pfeile das gezeichnete Diagramm hat. Die Reihenfolge der Knoten ist fest, damit nie ein Zyklus entsteht. "
                        "Entfernt man einen wahren Pfeil, behauptet das Diagramm mehr Unabhängigkeiten, als gelten.")
    st.button("↺ Diagramm der Welt wiederherstellen", width="stretch", on_click=reset_edges)
    st.markdown("**Frage**")
    x = st.selectbox("Knoten x", list(range(nn)), key="x_select", format_func=lambda v: names[v])
    y = st.selectbox("Knoten y", [v for v in range(nn) if v != x], key="y_select", format_func=lambda v: names[v])
    z = st.multiselect("Gegeben (Bedingungsmenge)", [v for v in range(nn) if v not in (x, y)], key="z_select", format_func=lambda v: names[v],
                       help="Welche Knoten man vorgibt. Ein Collider oder sein Nachfahre in der Menge öffnet den Pfad.")
    st.markdown("**Prüfung an Daten**")
    scope = st.selectbox("Welche Aussagen prüfen?", C.SCOPE_CHOICES, key="scope_select", format_func=lambda v: C.SCOPE_LABELS[v],
                         help="Die lokale Basis hat wenige Aussagen und damit wenige Mehrfachtests; die große Menge enthält alle d-Separationen mit höchstens zwei Bedingungen.")
    n = st.slider("Beobachtungen n", *bounds("n_slider"), step=C.N_STEP, key="n_slider", help="Stichprobengröße der simulierten Daten.")
    seed = st.number_input("Zufalls-Seed der Stichprobe", *bounds("seed_input"), key="seed_input", step=1)
    st.button("🎲 Neue Stichprobe würfeln", width="stretch", on_click=randomize_seed)

edges = claimed_edges()
sync_query_params({"w": world, "e": edges_text(edges), "x": x, "y": y, "z": ",".join(str(v) for v in z), "sc": scope, "n": int(n), "seed": int(seed)})

settings = Settings(world, edges, int(x), int(y), tuple(sorted(z)), scope, int(n), int(seed))
a = _analysis(settings)

# --- Ergebnis ------------------------------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Ergebnis")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Frage", "getrennt" if a.separated else "verbunden", delta=f"{sum(1 for p in a.paths if not p.blocked)} von {len(a.paths)} Pfaden offen", delta_color="off",
          help="d-getrennt heißt: Alle Pfade zwischen x und y sind blockiert; das Diagramm behauptet Unabhängigkeit, gegeben die Bedingungsmenge.")
c2.metric("Aussagen (Basis)", f"{a.n_basis}", delta=f"{a.n_cond2} mit bis zu 2 Bedingungen", delta_color="off",
          help="Lokale Markov-Basis: jeder Knoten ist von seinen Nicht-Nachfahren unabhängig, gegeben seine Eltern.")
c3.metric("Abgelehnt (roh)", f"{a.rejected_raw} von {len(a.statements)}", delta="Niveau 5 % je Aussage", delta_color="off")
c4.metric("Abgelehnt (Bonferroni)", f"{a.rejected_bonf} von {len(a.statements)}", delta="Niveau 5 % insgesamt", delta_color="off")

left, right = st.columns([1.1, 1])
with left:
    st.plotly_chart(build_diagram(a), width="stretch", key="diagram_chart")
    st.caption("Orange: Pfeile offener Pfade zwischen x und y. Dicker Rand: x und y; blau: vorgegebene Knoten. Hellgrau „fehlt“: ein wahrer Pfeil, den das gezeichnete "
               "Diagramm nicht hat; rot „überzählig“: ein Pfeil, den es in der Welt nicht gibt.")
with right:
    st.markdown("**Pfade zwischen x und y**")
    st.dataframe(build_paths_table(a), hide_index=True, width="stretch", height=min(60 + 35 * max(1, len(a.paths)), 360))
verdict(verdict_query(a))

if st.button("📄 PDF der aktuellen Prüfung erstellen", key="pdf_make"):
    st.session_state["pdf_made"] = (settings, build_pdf(a))
made = st.session_state.get("pdf_made")
if made and made[0] == settings:
    st.download_button("⬇️ PDF herunterladen", data=made[1], file_name="d-separation.pdf", mime="application/pdf", key="pdf_download")

# --- Kernfrage -----------------------------------------------------------------------------------------------------------------------------

st.markdown("## ❓ Kernfrage: Was behauptet dieses Diagramm, und stimmen die Daten?")
if a.statements:
    st.dataframe(style_statements(build_statements_table(a)), hide_index=True, width="stretch", height=min(60 + 35 * len(a.statements), 480))
    st.caption("„Gilt in der Welt“ ist die Antwort des wahren Diagramms (nicht der Daten). Abgelehnt heißt: Die Teilkorrelation weicht so stark von 0 ab, dass die "
               "behauptete Unabhängigkeit bei diesem n nicht mehr plausibel ist. Orange: roh abgelehnt; rot: auch mit Bonferroni.")
else:
    st.info("Dieses Diagramm behauptet keine Unabhängigkeit: Jedes Paar ist durch einen Pfeil verbunden, also gibt es nichts zu prüfen.")
verdict(verdict_check(a))
with st.expander("Alle Aussagen ohne Daten (nach Größe der Bedingungsmenge)"):
    full = separations(a.claimed, None)
    st.markdown(f"{len(full)} d-Separationen insgesamt, {a.n_cond2} mit höchstens zwei Bedingungen, lokale Basis {a.n_basis}.")
    st.markdown("\n".join(f"- {statement_text(a.names, s)}" for s in full) if full else "Keine.")

st.markdown("---")

# --- Experimente ---------------------------------------------------------------------------------------------------------------------------

st.subheader("🔬 Experiment 1: Bedingen kann Zusammenhang erzeugen")
res1 = _collider()
st.caption("A und B sind unabhängige Ursachen von C = A + B + 0,5ε; D = C + 0,5ε ist ein Nachfahre des Colliders C. Die Teilkorrelationen sind aus der Kovarianz "
           "exakt, die Auswahl C > 0 ist simuliert.")
st.plotly_chart(build_collider(res1), width="stretch", key="collider_chart")
verdict(verdict_collider(res1))

st.subheader("🔬 Experiment 2: Was das Diagramm behauptet, steckt in den fehlenden Pfeilen")
counts = _counts()
st.markdown("**Aussagenzahl je Welt**")
st.dataframe(
    [{"Welt": r["world"], "Knoten": r["nodes"], "Pfeile": r["edges"], "Lokale Basis": r["basis"], "Bis 2 Bedingungen": r["cond2"], "Alle": r["all"],
      "Vollständig": "ja" if r["complete"] else "nein"} for r in counts],
    hide_index=True, width="stretch")
st.caption("Das Stück-1-Diagramm hat alle drei Pfeile und damit 0 Aussagen: Es lässt sich an den Daten nicht prüfen, und das Diagramm mit umgedrehtem Pfeil "
           "zwischen Schwankung und Faktor behauptet ebenfalls nichts. Deshalb waren dort beide Lesarten gleich gut verträglich.")
rows2 = _claim()
st.plotly_chart(build_claim(rows2), width="stretch", key="claim_chart")
verdict(verdict_claim(rows2))
st.dataframe(
    [{"Diagramm": r["variant"], "n": r["n"], "Basisaussagen": r["k"], "davon in der Welt falsch": r["new"], "Abgelehnt (roh)": f"{de(100 * r['raw'], 0)} %",
      "Abgelehnt (Bonferroni)": f"{de(100 * r['bonf'], 0)} %"} for r in rows2],
    hide_index=True, width="stretch")
eq = _equivalence()
st.markdown("**Diagramme mit denselben Aussagen sind aus Daten nicht zu unterscheiden**")
st.dataframe(
    [{"Knoten": r["nodes"], "Diagramme (DAGs)": r["dags"], "Aussagenklassen": r["classes"], "Klassen mit nur einem Diagramm": r["singles"],
      "Größte Klasse": r["largest"], "Vollständige Diagramme (0 Aussagen)": r["complete"]} for r in eq],
    hide_index=True, width="stretch")
st.caption("Von 25 Diagrammen auf 3 Knoten unterscheiden sich nur 11 in ihren Aussagen. Wie man aus Daten die Klasse lernt, zeigt das Folgestück "
           "**Das Diagramm aus Daten lernen**.")

st.subheader("🔬 Experiment 3: Viele Aussagen, viele Tests")
st.caption(f"Das wahre 6-Knoten-Diagramm, n = {C.EXP_MULTI_N}, {C.EXP_MULTI_REPS} feste Wiederholungen. Gezählt wird, wie oft mindestens eine seiner eigenen, "
           "wahren Aussagen abgelehnt wird.")
rows3 = _multitest()
st.dataframe(
    [{"Aussagen": r["scope"], "Anzahl": r["k"], "Roh abgelehnt": f"{de(100 * r['raw'], 0)} %", "Naiv gerechnet (1 − 0,95^k)": f"{de(100 * r['naive'], 0)} %",
      "Mit Bonferroni": f"{de(100 * r['bonf'], 1)} %"} for r in rows3],
    hide_index=True, width="stretch")
verdict(verdict_multitest(rows3))

st.subheader("🔬 Experiment 4: Wie groß muss ein fehlender Pfeil sein?")
st.caption(f"Im gezeichneten Diagramm fehlt der Pfeil Faktor → Servicegrad; in der Welt hat er den Koeffizienten c. Anteil der Stichproben, in denen das Diagramm "
           f"mit Bonferroni abgelehnt wird ({C.EXP_POWER_REPS} feste Wiederholungen je Zelle).")
if st.button("🧮 Experiment 4 rechnen (rund 10 Sekunden)", key="power_run"):
    st.session_state["power_done"] = True
rows4 = None
if st.session_state.get("power_done", False):
    rows4 = _power()
    st.plotly_chart(build_power(rows4), width="stretch", key="power_chart")
    verdict(verdict_power(rows4))

st.markdown("---")

# --- Grenzen -------------------------------------------------------------------------------------------------------------------------------

st.subheader("🚧 Wo die Annahmen enden")
cls3 = next(r for r in eq if r["nodes"] == 3)
cls4 = next(r for r in eq if r["nodes"] == 4)
all_row = rows3[-1]
st.markdown(
    f"""
| Annahme | Was passiert, wenn sie verletzt ist | Wer setzt an |
|---|---|---|
| **Die Beziehungen sind linear und normalverteilt** | Der Test prüft lineare Teilkorrelation. Eine nichtlineare Abhängigkeit ohne Korrelation bleibt unsichtbar. | – |
| **Alle Größen sind beobachtet** | Eine unbeobachtete gemeinsame Ursache steht nicht im Diagramm und lässt Aussagen scheitern oder scheinbar halten. | Sensitivität und Falsifikation |
| **Ein Test je Aussage** | Bei {all_row['k']} Aussagen wird das wahre Diagramm roh in {de(100 * all_row['raw'], 0)} % der Stichproben abgelehnt (Experiment 3). | – |
| **Ablehnen heißt falsch, Nichtablehnen heißt richtig** | Ein überzähliger Pfeil behauptet weniger und wird nicht häufiger abgelehnt als das wahre Diagramm; aus {cls3['dags']} Diagrammen auf 3 Knoten werden nur {cls3['classes']} Aussagenklassen. | Wie falsch darf das Diagramm sein? |
| **Die Daten bestimmen das Diagramm** | Diagramme derselben Klasse sind aus Daten nicht zu trennen ({cls4['dags']} auf 4 Knoten, {cls4['classes']} Klassen). | Das Diagramm aus Daten lernen |
| **Die Aussagen legen die Pfeilrichtungen fest** | Eine Richtung ist nur festgelegt, wenn ein Collider sie erzwingt (auch indirekt über Folgekanten); Ketten und Gabeln mit denselben Aussagen sind nicht zu unterscheiden (A → M → B, A ← M ← B und A ← M → B bilden eine Klasse). | Das Diagramm aus Daten lernen |
| **Aussagen sagen, was man festhalten darf** | Welche Variable man festhalten muss, um eine Wirkung zu schätzen, folgt aus denselben Pfaden, braucht aber ein eigenes Kriterium. | Backdoor-Adjustierung |
"""
)

st.markdown("---")

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Diagramm.** Ein gerichteter azyklischer Graph $G$ auf den Knoten $V$; $\mathrm{pa}(v)$ sind die Eltern von $v$. Das Strukturmodell ist linear mit Einheitsrauschen,
$X = BX + \varepsilon$, also $\Sigma = (I-B)^{-1}(I-B)^{-\top}$.

**Pfad und Blockierung.** Ein Pfad zwischen $x$ und $y$ ist **blockiert** durch $Z$, wenn er einen Knoten $m$ enthält, der entweder eine Kette oder Gabel
($\to m \to$, $\leftarrow m \leftarrow$, $\leftarrow m \to$) ist und in $Z$ liegt, oder ein Collider ($\to m \leftarrow$), für den weder $m$ noch ein Nachfahre in $Z$ liegt.
$x$ und $y$ sind **d-getrennt** durch $Z$, wenn alle Pfade blockiert sind.

**Moralisierung.** Äquivalent: $x \perp_d y \mid Z$ genau dann, wenn $Z$ im ungerichteten moralisierten Graphen des Vorfahren-Graphen von $\{x,y\}\cup Z$ die Knoten $x$
und $y$ trennt (Eltern desselben Knotens werden verheiratet, Richtungen entfallen). Die Demo rechnet so; die Pfade dienen der Erklärung und als zweiter Rechenweg.

**Aussagen.** Jede d-Separation behauptet $x \perp\!\!\!\perp y \mid Z$. Im linearen Normalmodell ist das gleichbedeutend mit Teilkorrelation 0,
$\rho_{xy\cdot Z} = -P_{xy}/\sqrt{P_{xx}P_{yy}}$ mit $P$ als Inverse der Kovarianz der Teilmatrix $\{x,y\}\cup Z$. Die **lokale Markov-Basis** besteht aus
$v \perp\!\!\!\perp \mathrm{nd}(v)\setminus\mathrm{pa}(v) \mid \mathrm{pa}(v)$ für jeden Knoten $v$.

**Test.** Fisher-z: $z = \operatorname{artanh}(\hat\rho)\,\sqrt{n-|Z|-3}$, zweiseitiger p-Wert aus der Standardnormalverteilung. Bonferroni lehnt bei $p < \alpha/S$ ab,
$S$ ist die Zahl der Aussagen.

**Äquivalenz.** Zwei Diagramme mit gleicher Menge von d-Separationen heißen Markov-äquivalent. Hier gezählt über alle DAGs auf 3 und 4 Knoten.

**Literatur.** J. Pearl, *Probabilistic Reasoning in Intelligent Systems*, Morgan Kaufmann 1988; T. Verma, J. Pearl, *Equivalence and Synthesis of Causal Models*, 1990;
S. L. Lauritzen u. a., *Independence properties of directed Markov fields*, Networks 20, 1990 (alle aus dem Gedächtnis, nicht geprüft).
        """
    )

st.markdown("---")
st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zur Reihe: [Kausale Diagramme: von Konfundierung bis Wahl](https://sebastianhanisch.net/konzepte-kausale-diagramme.html)."
)
