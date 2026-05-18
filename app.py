"""
Extracció de dades analítiques OAC 360º — Interfície web
Desplega a Streamlit Community Cloud: https://share.streamlit.io
"""

import io
import calendar
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from api_client import AdtendeClient


# ─── Configuració de pàgina ──────────────────────────────────────────────────

st.set_page_config(
    page_title="OAC 360º — Extracció de dades",
    page_icon="📊",
    layout="centered",
)


# ─── Protecció per contrasenya ───────────────────────────────────────────────

def check_password():
    """Retorna True si l'usuari ha introduït la contrasenya correcta."""
    correct = st.secrets.get("APP_PASSWORD", "adtende2024")

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    st.title("📊 OAC 360º — Extracció de dades")
    st.markdown("---")
    pwd = st.text_input("Contrasenya d'accés", type="password", key="pwd_input")
    if st.button("Entrar"):
        if pwd == correct:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Contrasenya incorrecta.")
    return False


# ─── Utilitats de data ───────────────────────────────────────────────────────

def parse_date(s: str) -> date:
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            from datetime import datetime
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Format de data no reconegut: {s}")


def months_in_range(d_from: date, d_to: date):
    result = []
    y, m = d_from.year, d_from.month
    while (y, m) <= (d_to.year, d_to.month):
        result.append((y, m))
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return result


def month_window(year: int, month: int):
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return str(start), str(end)


# ─── Descàrrega i filtre ─────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def download_and_filter(municipio: str, d_from: date, d_to: date) -> pd.DataFrame:
    s_from = str(d_from)
    s_to   = str(d_to + timedelta(days=1))
    mesos  = months_in_range(d_from, d_to)

    client = AdtendeClient()
    client.login()

    dfs = []
    progress = st.progress(0, text="Descarregant dades...")
    for i, (y, m) in enumerate(mesos):
        m_from, m_to = month_window(y, m)
        filters = [{"type": "date", "variable": "td_managed",
                    "values": {"gte": m_from, "lt": m_to}}]
        df_m = client.query("tickets_enriquits", filters=filters)
        sub  = df_m[
            (df_m["des_client"]  == municipio) &
            (df_m["des_project"] == "OAC 360º")
        ].copy()
        dfs.append(sub)
        progress.progress((i + 1) / len(mesos),
                          text=f"Descarregant {y}-{m:02d}… ({len(sub)} tickets)")

    progress.empty()

    if not dfs:
        return pd.DataFrame()

    full = pd.concat(dfs, ignore_index=True)

    df = full[
        (full["td_managed"] >= s_from) & (full["td_managed"] < s_to) &
        (full["td_created"] >= s_from) & (full["td_created"] < s_to)
    ].copy()

    return df


# ─── Càlcul indicadors ───────────────────────────────────────────────────────

def calcular_indicadors(df: pd.DataFrame) -> list[dict]:
    total = len(df)
    if total == 0:
        return []

    pop_vals = df["val_population"].dropna()
    pop      = float(pop_vals.iloc[0]) if len(pop_vals) > 0 else None
    pct_pop  = f"{total / pop * 100:.2f}%" if pop else "N/D"
    pop_str  = f"{int(pop):,}".replace(",", ".") if pop else "N/D"

    enc   = df[(df["val_encuestable"] == 1) & (df["val_rating"].notna())]
    n_enc = len(enc)
    sat   = f"{enc['val_rating'].mean():.2f}"   if n_enc > 0 else "N/D"
    p1    = f"{enc['val_pregunta1'].mean():.2f}" if n_enc > 0 else "N/D"
    p2    = f"{enc['val_pregunta2'].mean():.2f}" if n_enc > 0 else "N/D"
    p3    = f"{enc['val_pregunta3'].mean():.2f}" if n_enc > 0 else "N/D"

    avg_t = df["val_time_spent"].mean()
    avg_m = int(avg_t)              if pd.notna(avg_t) else 0
    avg_s = int((avg_t - avg_m)*60) if pd.notna(avg_t) else 0

    trucam     = int(df["des_entry_channel"].isin(["TRUCA'M LOCUCIO", "TRUCA'M WEB"]).sum())
    tarda      = int((df["flg_morning_schedule"] == "15-24h").sum())
    cita       = int((df["des_category_0"] == "Cita Prèvia").sum())
    cat_tramits= int(df["des_category_1"].isin(["Catàleg de tràmits", "eTramitador"]).sum())
    campanyes  = int(df["des_category_1"].isin([
        "Estat dels meus expedients", "Inscripcions", "Processos selectius",
        "eNotificacions", "Signatura electrònica", "Carpeta del Ciutadà",
    ]).sum())
    centraleta = int((df["des_category_1"] == "Trucada per centraleta").sum())

    def pct(n): return f"{n / total * 100:.1f}%" if total else "0%"

    return [
        {"Indicador": "Total assistències",    "Valor": total,            "Detall": ""},
        {"Indicador": "Població (ref.)",        "Valor": pop_str,          "Detall": ""},
        {"Indicador": "% Població atesa",       "Valor": pct_pop,          "Detall": ""},
        {"Indicador": "Grau satisfacció /5",    "Valor": sat,              "Detall": f"n={n_enc}"},
        {"Indicador": "  Pregunta 1 /5",        "Valor": p1,               "Detall": ""},
        {"Indicador": "  Pregunta 2 /5",        "Valor": p2,               "Detall": ""},
        {"Indicador": "  Pregunta 3 /5",        "Valor": p3,               "Detall": ""},
        {"Indicador": "Temps mig consulta",     "Valor": f"{avg_m}m {avg_s:02d}s", "Detall": ""},
        {"Indicador": "Ús TRUCA'M",             "Valor": trucam,           "Detall": pct(trucam)},
        {"Indicador": "Franja tarda (15-24h)",  "Valor": tarda,            "Detall": pct(tarda)},
        {"Indicador": "Cita prèvia",            "Valor": cita,             "Detall": pct(cita)},
        {"Indicador": "Catàleg de tràmits",     "Valor": cat_tramits,      "Detall": pct(cat_tramits)},
        {"Indicador": "Campanyes puntuals",     "Valor": campanyes,        "Detall": pct(campanyes)},
        {"Indicador": "Trucades centraleta",    "Valor": centraleta,       "Detall": pct(centraleta)},
    ]


def generar_excel(df_ind: pd.DataFrame, df_raw: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_ind.to_excel(writer, sheet_name="Indicadors", index=False)
        df_raw.to_excel(writer, sheet_name="Dades raw",  index=False)
        ws = writer.sheets["Indicadors"]
        ws.column_dimensions["A"].width = 32
        ws.column_dimensions["B"].width = 16
        ws.column_dimensions["C"].width = 12
    return buf.getvalue()


# ─── Interfície principal ─────────────────────────────────────────────────────

def main():
    if not check_password():
        return

    st.title("📊 OAC 360º — Extracció de dades analítiques")
    st.markdown("Introdueix el municipi i el rang de dates per obtenir els 10 indicadors.")
    st.markdown("---")

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        municipio = st.text_input("Municipi", placeholder="Ex: Roses")
    with col2:
        d_from_input = st.date_input("Data inici", value=None, format="DD/MM/YYYY")
    with col3:
        d_to_input = st.date_input("Data fi", value=None, format="DD/MM/YYYY")

    st.markdown("")
    run = st.button("Extreure dades", type="primary", use_container_width=True)

    if run:
        # Validacions
        if not municipio:
            st.error("Cal introduir un municipi.")
            return
        if d_from_input is None or d_to_input is None:
            st.error("Cal seleccionar les dues dates.")
            return
        if d_to_input < d_from_input:
            st.error("La data fi ha de ser posterior a la data inici.")
            return

        with st.spinner("Connectant a l'API…"):
            try:
                df = download_and_filter(municipio, d_from_input, d_to_input)
            except Exception as e:
                st.error(f"Error en la descàrrega: {e}")
                return

        if df.empty:
            st.warning("No s'han trobat dades. Comprova el nom del municipi.")
            return

        indicadors = calcular_indicadors(df)
        if not indicadors:
            st.warning("No hi ha tickets en aquest rang.")
            return

        # Taula de resultats
        st.success(f"**{len(df):,} tickets** trobats per {municipio} · "
                   f"{d_from_input.strftime('%d/%m/%Y')} → {d_to_input.strftime('%d/%m/%Y')}")

        df_ind = pd.DataFrame(indicadors)
        st.dataframe(
            df_ind,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Indicador": st.column_config.TextColumn("Indicador", width="large"),
                "Valor":     st.column_config.TextColumn("Valor",     width="small"),
                "Detall":    st.column_config.TextColumn("Detall",    width="small"),
            }
        )

        # Botó de descàrrega
        excel_bytes = generar_excel(df_ind, df)
        filename = (f"informe_{municipio.replace(' ','_')}_"
                    f"{d_from_input.strftime('%Y%m%d')}_{d_to_input.strftime('%Y%m%d')}.xlsx")
        st.download_button(
            label="⬇️  Descarregar Excel",
            data=excel_bytes,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )


if __name__ == "__main__":
    main()
