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

BRAND   = "#54B9B3"
BRAND_D = "#3a9e98"   # fosc per hover
TEXT_D  = "#1a2e2d"

st.set_page_config(
    page_title="Adtende — Informes",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# CSS global
st.markdown(f"""
<style>
  /* Capçalera top */
  .header-bar {{
    background: {BRAND};
    padding: 18px 32px 14px 32px;
    border-radius: 10px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    gap: 14px;
  }}
  .header-bar h1 {{
    color: white;
    font-size: 1.5rem;
    margin: 0;
    font-weight: 700;
    letter-spacing: 0.02em;
  }}
  .header-bar span {{
    color: rgba(255,255,255,0.75);
    font-size: 0.9rem;
  }}

  /* Targetes de secció */
  .card {{
    background: #f8fefe;
    border: 1px solid #d4efed;
    border-radius: 10px;
    padding: 20px 24px;
    margin-bottom: 16px;
  }}

  /* Badge d'estat */
  .badge-ok  {{ background:#e6f7f6; color:#2a8a85; padding:3px 10px; border-radius:20px; font-size:.82rem; font-weight:600; }}
  .badge-err {{ background:#fdecea; color:#c0392b; padding:3px 10px; border-radius:20px; font-size:.82rem; font-weight:600; }}

  /* KPI cards */
  .kpi-wrap {{ display:flex; flex-wrap:wrap; gap:12px; margin:16px 0; }}
  .kpi {{
    background: white;
    border: 1px solid #d4efed;
    border-radius: 10px;
    padding: 14px 20px;
    min-width: 140px;
    flex: 1;
  }}
  .kpi .label {{ font-size:.75rem; color:#888; text-transform:uppercase; letter-spacing:.06em; }}
  .kpi .value {{ font-size:1.6rem; font-weight:700; color:{BRAND_D}; }}
  .kpi .sub   {{ font-size:.78rem; color:#aaa; }}

  /* Botó primari override */
  div.stButton > button[kind="primary"] {{
    background: {BRAND} !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    border-radius: 7px !important;
  }}
  div.stButton > button[kind="primary"]:hover {{
    background: {BRAND_D} !important;
  }}

  /* Tabs */
  .stTabs [data-baseweb="tab-list"] {{ gap: 8px; }}
  .stTabs [data-baseweb="tab"] {{
    border-radius: 8px 8px 0 0 !important;
    padding: 8px 20px !important;
  }}
  .stTabs [aria-selected="true"] {{
    background: {BRAND} !important;
    color: white !important;
  }}

  /* Oculta footer Streamlit */
  footer {{ visibility: hidden; }}
  #MainMenu {{ visibility: hidden; }}
</style>
""", unsafe_allow_html=True)


# ─── Auth ────────────────────────────────────────────────────────────────────

def check_password() -> bool:
    correct = st.secrets.get("APP_PASSWORD", "adtende2024")
    if st.session_state.get("auth"):
        return True
    st.markdown(f"""
    <div style="max-width:360px; margin:80px auto; text-align:center;">
      <div style="font-size:2.5rem;">📊</div>
      <h2 style="color:{BRAND}; margin:8px 0 4px;">Adtende Informes</h2>
      <p style="color:#888; font-size:.9rem;">Introdueix la contrasenya per accedir</p>
    </div>
    """, unsafe_allow_html=True)
    col = st.columns([1, 2, 1])[1]
    with col:
        pwd = st.text_input("Contrasenya", type="password", label_visibility="collapsed",
                            placeholder="Contrasenya…")
        if st.button("Entrar", type="primary", use_container_width=True):
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


def download_cache(client, d_from: date, d_to: date, municipio=None) -> pd.DataFrame:
    mesos = months_in_range(d_from, d_to)
    dfs   = []
    label = municipio or "GENERAL"
    bar   = st.progress(0, text=f"Descarregant dades {label}…")
    for i, (y, m) in enumerate(mesos):
        mf, mt = month_window(y, m)
        filters = [{"type": "date", "variable": "td_managed", "values": {"gte": mf, "lt": mt}}]
        df_m = client.query("tickets_enriquits", filters=filters)
        if municipio:
            sub = df_m[(df_m["des_client"] == municipio) & (df_m["des_project"] == "OAC 360º")].copy()
        else:
            sub = df_m[df_m["des_project"] == "OAC 360º"].copy()
        dfs.append(sub)
        bar.progress((i + 1) / len(mesos), text=f"{label} — {y}-{m:02d} ({len(sub)} tickets)")
    bar.empty()
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def filter_period(df, d_from: date, d_to: date) -> pd.DataFrame:
    s_from = str(d_from)
    s_to   = str(d_to + timedelta(days=1))
    return df[
        (df["td_managed"] >= s_from) & (df["td_managed"] < s_to) &
        (df["td_created"] >= s_from) & (df["td_created"] < s_to)
    ].copy().reset_index(drop=True)


# ─── Tab 1 — Informe de Servei ────────────────────────────────────────────────

MESOS_CA = ["Gener","Febrer","Març","Abril","Maig","Juny",
            "Juliol","Agost","Setembre","Octubre","Novembre","Desembre"]

def tab_servei():
    st.markdown("### 📄 Informe de Servei")
    st.caption("Genera els 5 documents Word mensuals (un per servei: OAC360, Social, Tributs, SATEDIBA, Centraleta)")

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        any_sel = st.selectbox("Any", list(range(2024, 2028)), index=2)
    with col2:
        mes_sel = st.selectbox("Mes", list(range(1, 13)),
                               format_func=lambda m: MESOS_CA[m - 1], index=date.today().month - 2)
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        generar = st.button("⚡ Generar 5 informes Word", type="primary", use_container_width=True)

    if generar:
        with st.spinner(f"Generant informes de {MESOS_CA[mes_sel-1]} {any_sel}…"):
            try:
                from report_generator import generate_all_monthly_reports
                fitxers = generate_all_monthly_reports(any_sel, mes_sel)
            except Exception as e:
                st.error(f"Error: {e}")
                return

        st.success(f"✅ {len(fitxers)} informes generats correctament")

        st.markdown("**Descarrega els fitxers:**")
        cols = st.columns(len(fitxers))
        for col, path in zip(cols, fitxers):
            with col:
                with open(path, "rb") as f:
                    data = f.read()
                nom = os.path.basename(path)
                servei = nom.replace(".docx", "").replace("_", " ")
                st.download_button(
                    label=f"⬇️ {servei}",
                    data=data,
                    file_name=nom,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )


# ─── Tab 2 — Informe de Client ────────────────────────────────────────────────

MUNICIPIS = [
    "OLOT", "CALDES DE MONTBUI", "ROSES", "CARDEDEU", "ESPARREGUERA",
    "SANTA PERPETUA DE MOGODA", "CASTELLÓ D'EMPÚRIES", "MOLLET DEL VALLÈS",
    "PALAFRUGELL", "VILANOVA I LA GELTRÚ",
]

def tab_client():
    st.markdown("### 🏛️ Informe de Client")
    st.caption("Taula KPI multi-període per municipi — genera Excel i obre el visor HTML")

    col1, col2 = st.columns([1, 2])
    with col1:
        muni = st.selectbox("Municipi", MUNICIPIS)
        custom = st.text_input("Altre municipi (majúscules)", placeholder="EX: SABADELL")
        municipio = custom.strip().upper() if custom.strip() else muni

    with col2:
        st.markdown("**Períodes** (fins a 4 rangs de dates)")
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
    generar = st.button("⚡ Generar informe client", type="primary", use_container_width=True)

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

        with st.spinner(f"Descarregant dades {municipio}…"):
            df_muni = download_cache(client, global_from, global_to, municipio=municipio)
        with st.spinner("Descarregant dades generals…"):
            df_gen  = download_cache(client, global_from, global_to, municipio=None)

        from sacar_datos import filter_period as fp, calcular_indicadors, \
                                 exportar_excel_multi_periode, generar_html_multi_periode

        ind_per = []
        for d_from, d_to in periodes_input:
            da = fp(df_muni, d_from, d_to)
            dg = fp(df_gen,  d_from, d_to)
            ia = calcular_indicadors(da, es_general=False)
            ig = calcular_indicadors(dg, es_general=True)
            ind_per.append((ia, ig))
            lbl = f"{d_from.strftime('%d/%m/%y')}–{d_to.strftime('%d/%m/%y')}"
            st.caption(f"✓ {lbl}: {len(da)} tickets {municipio} | {len(dg)} generals")

        # Excel
        excel_path = exportar_excel_multi_periode(municipio, periodes_input, ind_per)
        with open(excel_path, "rb") as f:
            excel_bytes = f.read()

        # HTML
        html = generar_html_multi_periode(municipio, periodes_input, ind_per)
        html_bytes = html.encode("utf-8")

        st.success("✅ Informe generat correctament")

        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                "⬇️ Descarregar Excel",
                data=excel_bytes,
                file_name=os.path.basename(excel_path),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        with c2:
            st.download_button(
                "⬇️ Descarregar HTML",
                data=html_bytes,
                file_name=f"informe_{municipio.lower().replace(' ','_')}.html",
                mime="text/html",
                use_container_width=True,
            )

        # Previsualització de la taula
        with st.expander("👁️ Previsualització taula", expanded=True):
            st.components.v1.html(html, height=600, scrolling=True)


# ─── Tab 3 — Informe d'Agent ─────────────────────────────────────────────────

from agent_report import (AGENTS, HORARI_AGENTS, calcular_minim_proporcional,
                           hores_mes_per_horari, MINIM_TRUCADES_PER_HORA_ACTIVA)

def tab_agent():
    st.markdown("### 👤 Informe d'Agent")
    st.caption("Càlcul del mínim exigible de trucades vs. trucades reals per a un agent i mes concrets")

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

    agent = AGENTS[agent_key]
    nom   = agent["nom"]

    # Horari del mes — previsualització
    with st.expander("📅 Horari del mes (editable per absències)", expanded=False):
        _, num_dies = calendar.monthrange(any_sel, mes_sel)
        DIA_NOM = {0:"Dl", 1:"Dm", 2:"Dc", 3:"Dj", 4:"Dv"}
        dies_data = []
        for dia in range(1, num_dies + 1):
            d = date(any_sel, mes_sel, dia)
            if d.weekday() >= 5:
                continue
            ns    = min(((d.day - 1) // 7) + 1, 4)
            cdia  = {0:"L", 1:"M", 2:"X", 3:"J", 4:"V"}[d.weekday()]
            hores = HORARI_AGENTS.get((agent_key, ns), {}).get(cdia, 0)
            dies_data.append({
                "Data":   d.strftime("%d/%m"),
                "Dia":    DIA_NOM[d.weekday()],
                "S":      ns,
                "Hores":  hores,
                "Absent": False,
            })
        df_dies = pd.DataFrame(dies_data)
        df_edit = st.data_editor(
            df_dies,
            column_config={
                "Data":   st.column_config.TextColumn("Data",   disabled=True),
                "Dia":    st.column_config.TextColumn("Dia",    disabled=True),
                "S":      st.column_config.NumberColumn("S",    disabled=True, width="small"),
                "Hores":  st.column_config.NumberColumn("Hores"),
                "Absent": st.column_config.CheckboxColumn("Absent"),
            },
            hide_index=True,
            use_container_width=True,
        )

    # Trucades reals
    col_t, col_b = st.columns([2, 1])
    with col_t:
        trucades_reals = st.number_input(
            "Trucades reals del mes",
            min_value=0, max_value=5000, value=0, step=1,
            help="Introdueix les trucades ateses per l'agent aquest mes"
        )
    with col_b:
        st.markdown("<br>", unsafe_allow_html=True)
        calcular = st.button("⚡ Calcular informe", type="primary", use_container_width=True)

    if calcular:
        # Llegir absències de la taula editada
        dies_absent = [
            date(any_sel, mes_sel, int(r["Data"].split("/")[0]))
            for _, r in df_edit.iterrows() if r["Absent"]
        ]

        # Hores reals (de la taula editada)
        hores_reals = sum(r["Hores"] for _, r in df_edit.iterrows() if not r["Absent"])
        dies_treballats = sum(1 for _, r in df_edit.iterrows() if not r["Absent"] and r["Hores"] > 0)

        minim = calcular_minim_proporcional(hores_reals, dies_treballats)

        diferencia = trucades_reals - minim["minim_exigible"]
        compliment = diferencia >= 0
        pct_real   = round(trucades_reals / minim["minim_exigible"] * 100) if minim["minim_exigible"] > 0 else 0

        # ── KPI cards ──
        estat_html = (
            f'<span class="badge-ok">✅ COMPLERT</span>'
            if compliment else
            f'<span class="badge-err">❌ NO COMPLERT</span>'
        )
        diff_color = BRAND_D if compliment else "#c0392b"

        st.markdown(f"""
        <div class="card">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
            <div>
              <span style="font-size:1.1rem; font-weight:700; color:{TEXT_D};">{nom}</span>
              &nbsp;<span style="color:#aaa; font-size:.85rem;">{agent_key} · {agent['rol']}</span>
            </div>
            <div>{estat_html}</div>
          </div>
          <div class="kpi-wrap">
            <div class="kpi">
              <div class="label">Hores jornada</div>
              <div class="value">{minim['hores_jornada']}h</div>
              <div class="sub">Dies: {minim['dies_treballats']}</div>
            </div>
            <div class="kpi">
              <div class="label">Hores actives</div>
              <div class="value">{minim['hores_actives']}h</div>
              <div class="sub">{minim['pct_jornada']}% jornada complerta</div>
            </div>
            <div class="kpi">
              <div class="label">Mínim exigible</div>
              <div class="value">{minim['minim_exigible']}</div>
              <div class="sub">trucades ({MINIM_TRUCADES_PER_HORA_ACTIVA}/h·activa)</div>
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

        # Detall absències
        if dies_absent:
            st.info(f"**{len(dies_absent)} dies d'absència** descomptats: "
                    + ", ".join(d.strftime("%d/%m") for d in dies_absent))

        # Botó descarregar Word (TODO: generar .docx quan es connecti Bizneo)
        st.caption("💡 Pròximament: descarrega l'informe com a Word un cop connectada la API Bizneo")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    if not check_password():
        return

    # Capçalera
    st.markdown(f"""
    <div class="header-bar">
      <span style="font-size:1.8rem;">📊</span>
      <div>
        <h1>Adtende Analytics</h1>
        <span>Generador d'informes — Servei · Client · Agent</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs([
        "📄  Informe de Servei",
        "🏛️  Informe de Client",
        "👤  Informe d'Agent",
    ])

    with tab1:
        tab_servei()
    with tab2:
        tab_client()
    with tab3:
        tab_agent()


if __name__ == "__main__":
    main()
