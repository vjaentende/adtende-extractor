"""
Adtende Analytics — Generador d'informes
=========================================
Interfície local per generar els 3 tipus d'informe sense consumir tokens d'IA.

Executa:  streamlit run app.py
"""

import io
import os
import calendar
from datetime import date, timedelta

import pandas as pd
import streamlit as st

# ─── Configuració de pàgina ──────────────────────────────────────────────────

BRAND   = "#14b8a6"   # teal-400
BRAND_D = "#0d9488"   # teal-500
GRAD    = "linear-gradient(135deg, #14b8a6 0%, #0891b2 100%)"
TEXT_D  = "#f1f5f9"   # slate-100
TEXT_M  = "#94a3b8"   # slate-400
BORDER  = "rgba(255,255,255,0.08)"
BG      = "#080d1a"
CARD_BG = "rgba(255,255,255,0.04)"
NAV_BG  = "#060a14"

st.set_page_config(
    page_title="Adtende Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

  html, body, [class*="css"], p, span, div, input, button, select {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
  }}

  /* ── Base ── */
  .stApp {{ background: {BG} !important; }}
  footer, #MainMenu, header[data-testid="stHeader"] {{ visibility: hidden; height: 0; }}
  .block-container {{
    padding-top: 0 !important;
    padding-bottom: 4rem !important;
    max-width: 1400px;
  }}

  /* ════ NAVBAR ════ */
  .navbar {{
    background: {NAV_BG};
    padding: 0 48px;
    height: 72px;
    display: flex; align-items: center; justify-content: space-between;
    margin: -1rem -1rem 52px -1rem;
    position: sticky; top: 0; z-index: 999;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    backdrop-filter: blur(20px);
  }}
  .navbar-brand {{ display:flex; align-items:center; gap:14px; }}
  .navbar-logo {{
    width: 38px; height: 38px;
    background: {GRAD};
    border-radius: 10px;
    display:flex; align-items:center; justify-content:center;
    box-shadow: 0 4px 16px rgba(20,184,166,0.35);
  }}
  .navbar-logo svg {{ width:20px; height:20px; fill:white; }}
  .navbar-title {{ font-size:1.1rem; font-weight:800; color:white; letter-spacing:-0.02em; }}
  .navbar-sep {{ width:1px; height:16px; background:rgba(255,255,255,0.12); }}
  .navbar-sub {{ font-size:0.82rem; color:rgba(255,255,255,0.3); font-weight:500; }}
  .navbar-badge {{
    font-size:0.68rem; font-weight:700; letter-spacing:0.08em; text-transform:uppercase;
    color:{BRAND}; background:rgba(20,184,166,0.12);
    padding:5px 14px; border-radius:20px; border:1px solid rgba(20,184,166,0.25);
  }}

  /* ════ TÍTOLS ════ */
  .section-heading {{
    font-size:2rem; font-weight:900; color:{TEXT_D};
    margin:0 0 8px; letter-spacing:-0.035em; line-height:1.15;
  }}
  .section-caption {{
    font-size:1.05rem; color:{TEXT_M}; margin-bottom:36px;
    font-weight:400; line-height:1.6;
  }}
  .label-group {{
    font-size:0.72rem; font-weight:700; color:{TEXT_M};
    text-transform:uppercase; letter-spacing:0.1em;
    margin:28px 0 12px; display:flex; align-items:center; gap:8px;
  }}
  .label-group::after {{
    content:''; flex:1; height:1px; background:{BORDER};
  }}

  /* ════ GLASS CARDS ════ */
  .card {{
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 20px; padding: 32px 36px; margin-bottom: 24px;
    backdrop-filter: blur(12px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.06);
  }}

  /* ════ BADGES ════ */
  .badge-ok {{
    display:inline-flex; align-items:center; gap:7px;
    background:rgba(34,197,94,0.12); color:#4ade80;
    padding:7px 18px; border-radius:30px;
    font-size:0.85rem; font-weight:700;
    border:1px solid rgba(74,222,128,0.25); letter-spacing:0.01em;
  }}
  .badge-err {{
    display:inline-flex; align-items:center; gap:7px;
    background:rgba(239,68,68,0.12); color:#f87171;
    padding:7px 18px; border-radius:30px;
    font-size:0.85rem; font-weight:700;
    border:1px solid rgba(248,113,113,0.25); letter-spacing:0.01em;
  }}

  /* ════ BOTONS ════ */
  div.stButton > button {{
    height:52px !important; border-radius:12px !important;
    font-weight:700 !important; font-size:1rem !important;
    transition:all .2s cubic-bezier(.4,0,.2,1) !important;
    letter-spacing:-0.01em !important;
  }}
  div.stButton > button[kind="primary"] {{
    background: {GRAD} !important;
    border:none !important; color:white !important;
    box-shadow:0 4px 16px rgba(20,184,166,0.35) !important;
  }}
  div.stButton > button[kind="primary"]:hover {{
    box-shadow:0 8px 28px rgba(20,184,166,0.5) !important;
    transform:translateY(-2px) !important;
  }}
  div.stButton > button[kind="secondary"] {{
    border:1px solid {BORDER} !important;
    background:rgba(255,255,255,0.04) !important;
    color:{TEXT_D} !important;
  }}
  div.stDownloadButton > button {{
    height:52px !important; border-radius:12px !important;
    font-weight:700 !important; font-size:1rem !important;
    transition:all .2s cubic-bezier(.4,0,.2,1) !important;
  }}
  div.stDownloadButton > button[kind="primary"] {{
    background:{GRAD} !important; border:none !important;
    color:white !important; box-shadow:0 4px 16px rgba(20,184,166,0.35) !important;
  }}
  div.stDownloadButton > button[kind="primary"]:hover {{
    box-shadow:0 8px 28px rgba(20,184,166,0.5) !important;
    transform:translateY(-2px) !important;
  }}
  div.stDownloadButton > button:not([kind="primary"]) {{
    border:1px solid {BORDER} !important;
    background:rgba(255,255,255,0.04) !important; color:{TEXT_D} !important;
  }}

  /* ════ TABS ════ */
  .stTabs [data-baseweb="tab-list"] {{
    gap:4px; border-bottom:1px solid {BORDER}; background:transparent;
  }}
  .stTabs [data-baseweb="tab"] {{
    border-radius:0 !important;
    padding:16px 32px !important;
    font-size:1rem !important; font-weight:600 !important;
    color:rgba(148,163,184,0.7) !important;
    border-bottom:2px solid transparent !important;
    margin-bottom:-1px !important; background:transparent !important;
    transition:all .2s ease !important;
  }}
  .stTabs [aria-selected="true"] {{
    color:#f1f5f9 !important;
    border-bottom-color:{BRAND} !important;
    font-weight:800 !important;
  }}
  .stTabs [data-baseweb="tab-panel"] {{ padding-top:32px; }}

  /* ════ INPUTS ════ */
  div[data-testid="stSelectbox"] > div > div,
  div[data-testid="stDateInput"] input,
  div[data-testid="stNumberInput"] input,
  div[data-testid="stTextInput"] input {{
    border-radius:10px !important; font-size:1rem !important;
    min-height:48px !important; font-weight:500 !important;
    background:rgba(255,255,255,0.05) !important;
    border-color:rgba(255,255,255,0.12) !important;
  }}
  label[data-testid="stWidgetLabel"] p {{
    font-size:0.9rem !important; font-weight:600 !important;
    color:rgba(148,163,184,0.9) !important; margin-bottom:6px !important;
  }}
  div[data-testid="stCheckbox"] label p {{
    font-size:1rem !important; font-weight:500 !important; color:{TEXT_D} !important;
  }}

  /* ════ ALERTS ════ */
  div[data-testid="stAlert"] {{
    border-radius:12px !important; font-size:0.95rem !important; font-weight:500 !important;
    background:rgba(255,255,255,0.04) !important; border:1px solid {BORDER} !important;
  }}

  /* ════ EXPANDER ════ */
  div[data-testid="stExpander"] {{
    border:1px solid {BORDER} !important; border-radius:14px !important;
    background:rgba(255,255,255,0.03) !important; box-shadow:none !important;
  }}
  div[data-testid="stExpander"] summary {{
    font-size:1rem !important; font-weight:600 !important;
    color:{TEXT_D} !important; padding:16px 20px !important;
  }}

  /* ════ PROGRESS ════ */
  div[data-testid="stProgressBar"] > div > div {{
    background:{GRAD} !important; border-radius:4px !important;
  }}
</style>
""", unsafe_allow_html=True)


# ─── Auth ────────────────────────────────────────────────────────────────────

def check_password() -> bool:
    correct = st.secrets.get("APP_PASSWORD", "adtende2024")
    if st.session_state.get("auth"):
        return True

    st.markdown(f"""
    <style>
      .stApp {{ background: radial-gradient(ellipse at 60% 0%, #0d2436 0%, {BG} 55%) !important; }}
      .login-outer {{
        max-width: 420px; margin: 90px auto 0; text-align: center;
      }}
      .login-glow {{
        width: 64px; height: 64px;
        background: {GRAD};
        border-radius: 18px; margin: 0 auto 24px;
        display: flex; align-items: center; justify-content: center;
        box-shadow: 0 0 48px rgba(20,184,166,0.45), 0 0 100px rgba(8,145,178,0.2);
      }}
      .login-title {{
        font-size: 1.75rem; font-weight: 900; letter-spacing: -0.04em;
        color: #f1f5f9; margin-bottom: 8px;
      }}
      .login-sub {{
        font-size: 1rem; color: rgba(148,163,184,0.75);
        margin-bottom: 36px; font-weight: 400; line-height: 1.5;
      }}
      .login-card {{
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.09);
        border-radius: 20px; padding: 36px 32px;
        backdrop-filter: blur(20px);
        box-shadow: 0 24px 64px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.06);
      }}
    </style>
    <div class="login-outer">
      <div class="login-glow">
        <svg viewBox="0 0 24 24" width="28" height="28" fill="white">
          <path d="M3 3h7v7H3zm11 0h7v7h-7zM3 14h7v7H3zm14 3a4 4 0 1 1 0-8 4 4 0 0 1 0 8z"/>
        </svg>
      </div>
      <div class="login-title">Adtende Analytics</div>
      <div class="login-sub">Plataforma d'informes automàtics</div>
      <div class="login-card">
    </div>
    """, unsafe_allow_html=True)

    col = st.columns([1, 2, 1])[1]
    with col:
        pwd = st.text_input("Contrasenya", type="password", label_visibility="collapsed",
                            placeholder="Contrasenya")
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if st.button("Accedir", type="primary", use_container_width=True):
            if pwd == correct:
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Contrasenya incorrecta")
    return False


# ─── Helpers API ─────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def get_client():
    from api_client import AdtendeClient
    c = AdtendeClient()
    c.login()
    return c


def months_in_range(d_from: date, d_to: date):
    r, y, m = [], d_from.year, d_from.month
    while (y, m) <= (d_to.year, d_to.month):
        r.append((y, m)); m += 1
        if m > 12: y, m = y + 1, 1
    return r


def month_window(y, m):
    s = date(y, m, 1)
    e = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)
    return str(s), str(e)


@st.cache_data(ttl=3600, show_spinner=False)
def _download_mes_cached(any_: int, mes: int, municipio: str | None) -> pd.DataFrame:
    """Descàrrega d'UN sol mes, amb cache d'1h. Clau: (any, mes, municipio)."""
    client = get_client()
    mf, mt = month_window(any_, mes)
    filters = [{"type": "date", "variable": "td_managed", "values": {"gte": mf, "lt": mt}}]
    df_m = client.query("tickets_enriquits", filters=filters)
    if municipio:
        return df_m[(df_m["des_client"] == municipio) & (df_m["des_project"] == "OAC 360º")].copy()
    return df_m[df_m["des_project"] == "OAC 360º"].copy()


def download_cache(client, d_from: date, d_to: date, municipio=None) -> pd.DataFrame:
    """Descàrrega mes a mes amb cache. Si un mes ja s'ha baixat en aquesta sessió, no el repeteix."""
    mesos = months_in_range(d_from, d_to)
    label = municipio or "GENERAL"
    bar   = st.progress(0, text=f"Descarregant {label}…")
    dfs   = []
    for i, (y, m) in enumerate(mesos):
        bar.progress((i + 1) / len(mesos), text=f"{label} — {y}-{m:02d}…")
        sub = _download_mes_cached(y, m, municipio)
        dfs.append(sub)
    bar.empty()
    full = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    # Aplica filtre de rang exacte
    s_from = str(d_from)
    s_to   = str(d_to + timedelta(days=1))
    if not full.empty and "td_managed" in full.columns:
        full = full[
            (full["td_managed"] >= s_from) & (full["td_managed"] < s_to) &
            (full["td_created"] >= s_from) & (full["td_created"] < s_to)
        ].copy().reset_index(drop=True)
    return full


def filter_period(df, d_from: date, d_to: date) -> pd.DataFrame:
    s_from = str(d_from)
    s_to   = str(d_to + timedelta(days=1))
    return df[
        (df["td_managed"] >= s_from) & (df["td_managed"] < s_to) &
        (df["td_created"] >= s_from) & (df["td_created"] < s_to)
    ].copy().reset_index(drop=True)


# ─── Component React KPI ─────────────────────────────────────────────────────

def render_kpi_react(kpis: list[dict], height: int = 180) -> None:
    """
    Renderitza una fila de KPI cards com a component React amb count-up animation.
    kpis: [{"label": str, "value": str|int|float, "sub": str, "accent": bool}]
    """
    import json, html as _html
    kpis_json = json.dumps(kpis)
    st.components.v1.html(f"""
<!DOCTYPE html>
<html>
<head>
<script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
<script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
<style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:transparent; font-family:'Inter',-apple-system,sans-serif; }}
  .wrap {{
    display:flex; gap:14px; flex-wrap:wrap;
    padding:4px 2px;
  }}
  .kpi {{
    flex:1; min-width:140px;
    background:rgba(255,255,255,0.04);
    border:1px solid rgba(255,255,255,0.09);
    border-radius:16px; padding:22px 24px;
    transition:transform .2s ease, box-shadow .2s ease;
    cursor:default;
  }}
  .kpi:hover {{
    transform:translateY(-3px);
    box-shadow:0 12px 40px rgba(0,0,0,0.4);
    border-color:rgba(20,184,166,0.3);
  }}
  .kpi.accent {{ border-color:rgba(20,184,166,0.35); }}
  .kpi.accent .val {{ background:linear-gradient(135deg,#14b8a6,#0891b2); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }}
  .lbl {{
    font-size:0.7rem; font-weight:700; letter-spacing:0.1em;
    text-transform:uppercase; color:#64748b; margin-bottom:10px;
  }}
  .val {{
    font-size:2.5rem; font-weight:900; color:#f1f5f9;
    letter-spacing:-0.04em; line-height:1;
    margin-bottom:8px;
  }}
  .sub {{ font-size:0.8rem; color:#64748b; font-weight:500; }}
</style>
</head>
<body>
<div id="root"></div>
<script>
const {{ useState, useEffect }} = React;

function useCountUp(target, duration=900) {{
  const isNum = typeof target === 'number';
  const [cur, setCur] = useState(isNum ? 0 : target);
  useEffect(() => {{
    if (!isNum) {{ setCur(target); return; }}
    let start = null;
    const from = 0;
    function step(ts) {{
      if (!start) start = ts;
      const p = Math.min((ts - start) / duration, 1);
      const ease = 1 - Math.pow(1 - p, 3);
      setCur(Math.round(from + (target - from) * ease));
      if (p < 1) requestAnimationFrame(step);
    }}
    requestAnimationFrame(step);
  }}, [target]);
  return cur;
}}

function KpiCard({{ label, value, sub, accent }}) {{
  const numVal = typeof value === 'string' ? parseFloat(value.replace(/[^0-9.-]/g,'')) : value;
  const isNumeric = !isNaN(numVal) && typeof value !== 'string' || /^[0-9.]+$/.test(String(value));
  const animated = useCountUp(isNumeric ? numVal : 0);
  const display = isNumeric ? (Number.isInteger(numVal) ? animated : animated.toFixed(1)) : value;

  return React.createElement('div', {{ className: `kpi${{accent?' accent':''}}` }},
    React.createElement('div', {{ className:'lbl' }}, label),
    React.createElement('div', {{ className:'val' }}, isNumeric ? display : value),
    React.createElement('div', {{ className:'sub' }}, sub)
  );
}}

function App() {{
  const kpis = {kpis_json};
  return React.createElement('div', {{ className:'wrap' }},
    kpis.map((k,i) => React.createElement(KpiCard, {{ key:i, ...k }}))
  );
}}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(React.createElement(App));
</script>
</body>
</html>
""", height=height)


# ─── Tab 1 — Informe de Servei ────────────────────────────────────────────────

MESOS_CA = ["Gener","Febrer","Març","Abril","Maig","Juny",
            "Juliol","Agost","Setembre","Octubre","Novembre","Desembre"]

SERVEIS_OPCIONS = {
    "OAC 360":        "oac360",
    "OAC 360 Social": "oac360_social",
    "OAC 360 Tributs":"oac360_tributs",
    "SATE DIBA":      "satediba",
    "Centraleta":     "centraleta",
}

def tab_servei():
    st.markdown('<p class="section-heading">Informe de Servei</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-caption">Genera els informes Word mensuals dels serveis seleccionats</p>', unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])
    with col1:
        any_sel = st.selectbox("Any", list(range(2024, 2028)), index=2)
    with col2:
        mes_sel = st.selectbox("Mes", list(range(1, 13)),
                               format_func=lambda m: MESOS_CA[m - 1], index=date.today().month - 2)

    st.markdown('<div class="label-group">Serveis a generar</div>', unsafe_allow_html=True)
    cols_cb = st.columns(5)
    seleccionats = []
    for col, (nom_servei, key) in zip(cols_cb, SERVEIS_OPCIONS.items()):
        with col:
            if st.checkbox(nom_servei, value=True, key=f"svc_{key}"):
                seleccionats.append(key)

    st.markdown("")
    n = len(seleccionats)
    label_btn = f"Generar {n} informe{'s' if n != 1 else ''} Word" if n > 0 else "Selecciona almenys un servei"
    generar = st.button(label_btn, type="primary", use_container_width=True, disabled=(n == 0))

    if generar:
        from report_generator import SERVICES, _apply_dual_date_filter, _build_docx, MESOS
        from api_client import AdtendeClient
        from pathlib import Path

        svcs_sel = [s for s in SERVICES if s["key"] in seleccionats]
        mes_nom  = MESOS[mes_sel]

        with st.spinner("Connectant a l'API…"):
            try:
                client = AdtendeClient()
                client.login()
            except Exception as e:
                st.error(f"Error de connexió: {e}")
                return

        fitxers = []
        errors  = []
        bar = st.progress(0, text="Generant informes…")

        for i, svc in enumerate(svcs_sel):
            bar.progress(i / len(svcs_sel), text=f"Generant {svc['name']}…")
            try:
                df = client.query_month(
                    svc["endpoint"], any_sel, mes_sel,
                    date_field=svc["date_field"],
                    project=svc["project"],
                )
                df = _apply_dual_date_filter(df, any_sel, mes_sel)
                if df.empty:
                    errors.append(f"{svc['name']}: sense dades per aquest mes")
                    continue
                fname = f"informe_{any_sel}_{mes_sel:02d}_{mes_nom}_{svc['slug']}.docx"
                title = f"{svc['name']} — {mes_nom} {any_sel}"
                _build_docx(df, any_sel, mes_sel, title, Path(fname))
                with open(fname, "rb") as f:
                    fitxers.append({"nom": fname, "data": f.read(), "slug": svc["slug"]})
            except Exception as e:
                msg = str(e)
                if "502" in msg or "503" in msg or "504" in msg:
                    errors.append(f"{svc['name']}: error temporal de l'API (502) — torna a intentar-ho")
                else:
                    errors.append(f"{svc['name']}: {msg}")

        bar.progress(1.0, text="Fet!")
        bar.empty()

        # Guardar a session_state per persistir entre descàrregues
        if fitxers:
            st.session_state["servei_fitxers"] = fitxers
            st.session_state["servei_errors"]  = errors

    # Mostrar botons de descàrrega (persisteix fins a nova generació)
    fitxers_guardats = st.session_state.get("servei_fitxers", [])
    errors_guardats  = st.session_state.get("servei_errors",  [])

    if fitxers_guardats:
        n_ok = len(fitxers_guardats)
        st.success(f"{n_ok} informe{'s' if n_ok != 1 else ''} generat{'s' if n_ok != 1 else ''} correctament")

        # Botó ZIP (descarregar tots)
        if len(fitxers_guardats) > 1:
            import zipfile
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in fitxers_guardats:
                    zf.writestr(f["nom"], f["data"])
            zip_buf.seek(0)
            nom_zip = fitxers_guardats[0]["nom"].rsplit("_", 1)[0] + "_TOTS.zip"
            st.download_button(
                label=f"Descarregar tots ({len(fitxers_guardats)} fitxers) — ZIP",
                data=zip_buf.getvalue(),
                file_name=nom_zip,
                mime="application/zip",
                use_container_width=True,
                key="dl_zip",
                type="primary",
            )

        # Botons individuals
        cols = st.columns(len(fitxers_guardats))
        for col, f in zip(cols, fitxers_guardats):
            with col:
                st.download_button(
                    label=f"{f['slug']}",
                    data=f["data"],
                    file_name=f["nom"],
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                    key=f"dl_{f['slug']}",
                )
    for e in errors_guardats:
        st.warning(e)


# ─── Tab 2 — Informe de Client ────────────────────────────────────────────────

MUNICIPIS = sorted([
    "Abella de la Conca", "Abrera", "Ager", "Agramunt", "Aitona",
    "Alamús, els", "Albatarrec", "Albesa", "Alcanó", "Alcarràs",
    "Alcoletge", "Alella", "Alguaire", "Almacelles", "Almatret",
    "Almenar", "Alpens", "Alpicat", "Alt Aneu", "Alòs de Balaguer",
    "Anglesola", "Arbeca", "Arres", "Artesa de Segre",
    "Bagà", "Balaguer", "Balsareny", "Baronia de Rialb, la",
    "Barruera - Vall de Boí", "Bausén", "Bellaguarda", "Bellver de Cerdanya",
    "Bellvís", "Benavent de Segrià", "Borges Blanques, les", "Bossost", "Bovera",
    "CALDES DE MONTBUI", "CALVIA", "CAMBRILS", "CASTELLBISBAL",
    "CASTELLET I LA GORNAL", "CASTELLO EMPURIES", "CORNELLA DE LLOBREGAT",
    "Cabrera d'Anoia", "Cabrils", "Camarasa", "Canovelles", "Cardedeu",
    "Castellbisbal", "Castelldans", "Castellolí", "Castellserà",
    "Castellví de la Marca", "Castelló de Farfanya", "Cercs", "Cervera",
    "Cervià de les Garrigues", "Cogul, el", "Coll de Nargó",
    "Coma i la Pedra, la", "Cubelles", "Cubells",
    "Dosrius", "EMU LLEIDA", "Espot", "Esquirol", "Esterri d'Àneu",
    "ESPARREGUERA", "Farrera", "Figaró-Montmany", "Fogars de la Selva",
    "Folgueroles", "Fonollosa", "Fulleda", "Fígols i Alinya",
    "GAVA", "GRANOLLERS", "Gaià", "Golmés", "Granada", "Granadella, la",
    "Guingueta d'Àneu", "Guissona",
    "Hostalets de Pierola", "Isona i Conca Dellà", "Ivars de Noguera",
    "Jorba", "Josa i Tuixen", "Juneda",
    "LLEIDA", "LLORET DE MAR", "La Llacuna", "Les", "Linyola", "Llardecans",
    "MASQUEFA", "MATADEPERA", "MOLLET DEL VALLES", "MONT-ROIG DEL CAMP",
    "MONTCADA I REIXAC", "Maials", "Maldà", "Malgrat de Mar",
    "Masies de Roda", "Masies de Voltregà", "Miralcamp", "Mollerussa",
    "Monistrol de Montserrat", "Montellà i Martinet", "Montesquiu",
    "Montferrer i Castellbó", "Montgat", "Montmeló", "Montoliu de Lleida", "Mura",
    "Naut Aran", "OLOT", "Oliana", "Oliola", "Olius", "Oluges, les",
    "Organyà", "Os de Balaguer",
    "PALAU-SOLITA I PLEGAMANS", "PRAT DE LLOBREGAT", "PREMIA DE MAR",
    "Palafolls", "Palma de Cervelló", "Papiol", "Penelles", "Pinós",
    "Pla del Penedès", "Pobla de Claramunt", "Pobla de Cèrvoles, la",
    "Pobla de Segur, la", "Pont de Suert", "Pont de Vilomara i Rocafort",
    "Ponts", "Puig-reig", "Puigverd de Lleida", "Pujalt",
    "ROSES", "Rajadell", "Riner", "Roca del Vallès", "Rosselló", "Rupit i Pruit",
    "SALT", "SANT ESTEVE SESROVIRES", "SANT FELIU DE LLOBREGAT",
    "SANT VICENÇ DELS HORTS", "SANTA PERPETUA DE MOGODA", "SITGES",
    "Salàs de Pallars", "Sanaüja", "Sant Antoni de Vilamajor",
    "Sant Cebrià de Vallalta", "Sant Esteve Sesrovires", "Sant Feliu de Codines",
    "Sant Guim de Freixenet", "Sant Hipòlit de Voltregà", "Sant Llorenç d'Hortons",
    "Sant Martí Sarroca", "Sant Pere Sallavinera", "Sant Quintí de Mediona",
    "Santa Eulàlia de Riuprimer", "Santa Maria d'Oló", "Santa Maria de Miralles",
    "Seu d'Urgell, La", "Soleràs, el", "Solsona", "Sort", "Soses",
    "Subirats", "Sudanell", "Sunyer",
    "Talamanca", "Talarn", "Tordera", "Torre de Cabdella, la", "Torre de Claramunt",
    "Torrebesses", "Torrefarrera", "Torrefeta i Florejacs", "Torregrossa",
    "Torrelameu", "Torrelles de Foix", "Torrelles de Llobregat", "Torres de Segre",
    "Tremp", "Tàrrega", "Tírvia",
    "VIC", "VILASSAR DE DALT", "Vacarisses", "Vallbona d'Anoia",
    "Vallbona de les Monges", "Vallfogona de Balaguer", "Vansa i Fórnols, la",
    "Vielha e Mijaran", "Vilaller", "Vilamós", "Vilanova de Bellpuig",
    "Vilanova de Meià", "Vilanova de Segrià", "Vilanova de la Barca",
    "Vilosell, el", "Vinaixa",
], key=lambda x: x.lower())

def tab_client():
    st.markdown('<p class="section-heading">Informe de Client</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-caption">Taula KPI multi-període per municipi — genera Excel i visor HTML</p>', unsafe_allow_html=True)

    col1, col2 = st.columns([1, 2])
    with col1:
        municipio = st.selectbox("Municipi", MUNICIPIS)

    with col2:
        st.markdown('<div class="label-group">Períodes (fins a 4 rangs de dates)</div>', unsafe_allow_html=True)
        periodes_input = []
        for i in range(4):
            c1, c2, c3 = st.columns([1, 1, 1])
            with c1:
                actiu = st.checkbox(f"Període {i+1}", value=(i < 2), key=f"p{i}_on")
            if actiu:
                with c2:
                    d_from = st.date_input(f"Inici {i+1}", value=date(2024 - i, 10, 1),
                                           format="DD/MM/YYYY", key=f"p{i}_from")
                with c3:
                    d_to = st.date_input(f"Fi {i+1}", value=date(2025 - i, 10, 1),
                                         format="DD/MM/YYYY", key=f"p{i}_to")
                if d_from and d_to and d_to > d_from:
                    periodes_input.append((d_from, d_to))

    st.markdown("")
    generar = st.button("Generar informe", type="primary", use_container_width=True)

    if generar:
        if not periodes_input:
            st.error("Cal definir almenys un període vàlid.")
            return

        try:
            client = get_client()
        except Exception as e:
            st.error(f"Error de connexió API: {e}")
            return

        global_from = min(d for d, _ in periodes_input)
        global_to   = max(d for _, d in periodes_input)

        from sacar_datos import calcular_indicadors, \
                                 exportar_excel_multi_periode, generar_html_multi_periode

        ind_per  = []
        statuses = [st.empty() for _ in periodes_input]

        for i, (d_from, d_to) in enumerate(periodes_input):
            lbl = f"{d_from.strftime('%d/%m/%y')}–{d_to.strftime('%d/%m/%y')}"
            statuses[i].info(f"⏳ Descarregant període {i+1}: {lbl}…")
            try:
                da = download_cache(client, d_from, d_to, municipio=municipio)
                dg = download_cache(client, d_from, d_to, municipio=None)
            except Exception as e:
                msg = str(e)
                if "502" in msg or "503" in msg or "504" in msg:
                    statuses[i].error(f"Període {i+1}: error temporal de l'API (502) — torna a intentar-ho")
                else:
                    statuses[i].error(f"Període {i+1}: {msg}")
                return

            ia = calcular_indicadors(da, es_general=False)
            ig = calcular_indicadors(dg, es_general=True)
            ind_per.append((ia, ig))
            statuses[i].success(f"✓ Període {i+1}: {len(da)} tickets {municipio} | {len(dg)} generals")

        if not ind_per:
            return

        # Excel
        excel_path = exportar_excel_multi_periode(municipio, periodes_input, ind_per)
        with open(excel_path, "rb") as f:
            excel_bytes = f.read()

        # HTML
        html = generar_html_multi_periode(municipio, periodes_input, ind_per)
        html_bytes = html.encode("utf-8")

        st.success("Informe generat correctament")

        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                "Descarregar Excel",
                data=excel_bytes,
                file_name=os.path.basename(excel_path),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="primary",
            )
        with c2:
            st.download_button(
                "Descarregar HTML",
                data=html_bytes,
                file_name=f"informe_{municipio.lower().replace(' ','_')}.html",
                mime="text/html",
                use_container_width=True,
            )

        # Previsualització de la taula
        with st.expander("Previsualització", expanded=True):
            st.components.v1.html(html, height=600, scrolling=True)


# ─── Tab 3 — Informe d'Agent ─────────────────────────────────────────────────

from agent_report import (
    AGENTS, BizneoClie, calcular_minim, dies_laborables_mes,
    MINIM_TRUCADES_HORA, TRUCADES_DIA_JORNADA_COMPLERTA,
)

@st.cache_resource(show_spinner=False)
def _bizneo_client():
    return BizneoClie()

def tab_agent():
    st.markdown('<p class="section-heading">Informe d\'Agent</p>', unsafe_allow_html=True)
    st.markdown('<p class="section-caption">Càlcul del mínim exigible de trucades vs. trucades reals per a un agent i mes concrets</p>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        agent_key = st.selectbox(
            "Agent",
            list(AGENTS.keys()),
            format_func=lambda k: f"{AGENTS[k]['nom']} ({k})"
        )
    with col2:
        any_sel = st.selectbox("Any ", list(range(2024, 2028)), index=2, key="ag_any")
    with col3:
        mes_sel = st.selectbox("Mes ", list(range(1, 13)),
                               format_func=lambda m: MESOS_CA[m - 1],
                               index=date.today().month - 2, key="ag_mes")

    agent       = AGENTS[agent_key]
    nom         = agent["nom"]
    te_bizneo   = agent["bizneo_id"] is not None
    biz_key     = f"biz_abs_{agent_key}_{any_sel}_{mes_sel}"

    # ── Càrrega d'absències Bizneo ──────────────────────────────────────────
    col_biz, col_info = st.columns([1, 3])
    with col_biz:
        carregar_biz = st.button(
            "Carregar absències Bizneo",
            type="secondary",
            use_container_width=True,
            disabled=not te_bizneo,
            help="Obté les absències aprovades d'aquest agent des de Bizneo HCM"
                 if te_bizneo else "Aquest agent no té ID Bizneo configurat",
        )
    with col_info:
        if not te_bizneo:
            st.caption(f"{nom} no té ID Bizneo — marca les absències manualment a la taula")

    if carregar_biz:
        with st.spinner("Connectant amb Bizneo..."):
            biz  = _bizneo_client()
            dies = biz.dies_absencia_mes(agent["bizneo_id"], any_sel, mes_sel)
        st.session_state[biz_key] = [d.strftime("%d/%m") for d in dies]
        if dies:
            st.success(f"{len(dies)} dies d'absència carregats de Bizneo")
        else:
            st.info("Cap absència aprovada trobada a Bizneo per aquest mes")

    dies_bizneo = set(st.session_state.get(biz_key, []))

    # ── Taula de dies laborables (absent editable) ──────────────────────────
    with st.expander("Dies laborables del mes (marca absències)", expanded=False):
        DIA_NOM = {0: "Dl", 1: "Dm", 2: "Dc", 3: "Dj", 4: "Dv"}
        dies_data = []
        for d in dies_laborables_mes(any_sel, mes_sel):
            data_str = d.strftime("%d/%m")
            dies_data.append({
                "Data":   data_str,
                "Dia":    DIA_NOM[d.weekday()],
                "Absent": data_str in dies_bizneo,
            })
        df_dies = pd.DataFrame(dies_data)
        df_edit = st.data_editor(
            df_dies,
            column_config={
                "Data":   st.column_config.TextColumn("Data",  disabled=True),
                "Dia":    st.column_config.TextColumn("Dia",   disabled=True, width="small"),
                "Absent": st.column_config.CheckboxColumn("Absent"),
            },
            hide_index=True,
            use_container_width=True,
            key=f"taula_{agent_key}_{any_sel}_{mes_sel}",
        )

    # ── Trucades reals + botó ───────────────────────────────────────────────
    col_t, col_b = st.columns([2, 1])
    with col_t:
        trucades_reals = st.number_input(
            "Trucades reals del mes",
            min_value=0, max_value=5000, value=0, step=1,
            help="Introdueix les trucades ateses per l'agent aquest mes"
        )
    with col_b:
        st.markdown("<br>", unsafe_allow_html=True)
        calcular = st.button("Calcular informe", type="primary", use_container_width=True)

    if calcular:
        dies_absent = [
            date(any_sel, mes_sel, int(r["Data"].split("/")[0]))
            for _, r in df_edit.iterrows() if r["Absent"]
        ]
        dies_absent_set = set(dies_absent)
        tots_dies       = dies_laborables_mes(any_sel, mes_sel)
        dies_treballats = len([d for d in tots_dies if d not in dies_absent_set])

        minim      = calcular_minim(agent["hores_setmana"], dies_treballats)
        diferencia = trucades_reals - minim["minim_exigible"]
        compliment = diferencia >= 0
        pct_real   = round(trucades_reals / minim["minim_exigible"] * 100) if minim["minim_exigible"] > 0 else 0

        estat_html = (
            '<span class="badge-ok">Complert</span>'
            if compliment else
            '<span class="badge-err">No complert</span>'
        )
        diff_color = BRAND_D if compliment else "#dc2626"
        font_biz   = "Bizneo" if (te_bizneo and dies_bizneo) else "Manual"

        st.markdown(f"""
        <div class="card">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
            <div>
              <span class="agent-name">{nom}</span>
              &nbsp;&nbsp;<span class="agent-role">{agent_key} · {agent['rol']}</span>
            </div>
            <div>{estat_html}</div>
          </div>
          <div class="kpi-wrap">
            <div class="kpi">
              <div class="label">Dies laborables</div>
              <div class="value">{len(tots_dies)}</div>
              <div class="sub">Absències: {len(dies_absent)} [{font_biz}]</div>
            </div>
            <div class="kpi">
              <div class="label">Dies treballats</div>
              <div class="value">{dies_treballats}</div>
              <div class="sub">{minim['pct_jornada']}% del mes complet</div>
            </div>
            <div class="kpi">
              <div class="label">Mínim exigible</div>
              <div class="value">{minim['minim_exigible']}</div>
              <div class="sub">{minim['trucades_dia']} tru/dia · {MINIM_TRUCADES_HORA}/h</div>
            </div>
            <div class="kpi">
              <div class="label">Trucades reals</div>
              <div class="value" style="color:{diff_color};">{trucades_reals}</div>
              <div class="sub">{pct_real}% del mínim</div>
            </div>
            <div class="kpi">
              <div class="label">Diferència</div>
              <div class="value" style="color:{diff_color};">{diferencia:+d}</div>
              <div class="sub">trucades</div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        if dies_absent:
            st.info(f"**{len(dies_absent)} dies d'absència** descomptats "
                    f"[{font_biz}]: "
                    + ", ".join(d.strftime("%d/%m") for d in sorted(dies_absent)))


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    if not check_password():
        return

    # Navbar
    st.markdown(f"""
    <div class="navbar">
      <div class="navbar-brand">
        <div class="navbar-logo">
          <svg viewBox="0 0 24 24" fill="white">
            <path d="M3 3h7v7H3zm11 0h7v7h-7zM3 14h7v7H3zm14 3a4 4 0 1 1 0-8 4 4 0 0 1 0 8z"/>
          </svg>
        </div>
        <span class="navbar-title">Adtende Analytics</span>
        <div class="navbar-sep"></div>
        <span class="navbar-sub">Generador d'informes</span>
      </div>
      <span class="navbar-badge">Ús intern</span>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs([
        "Informe de Servei",
        "Informe de Client",
        "Informe d'Agent",
    ])

    with tab1:
        tab_servei()
    with tab2:
        tab_client()
    with tab3:
        tab_agent()


if __name__ == "__main__":
    main()
