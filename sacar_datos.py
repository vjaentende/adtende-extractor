#!/usr/bin/env python3
"""
Extracció de dades analítiques per municipi i rang de dates.

Executa:  python sacar_datos.py
"""

import sys
import calendar
from datetime import date, timedelta

import pandas as pd

from api_client import AdtendeClient


# ─── Utilitats de data ────────────────────────────────────────────────────────

def parse_date(s: str) -> date:
    """Accepta DD/MM/YYYY o DD/MM/YY i retorna un objecte date."""
    parts = s.strip().replace("-", "/").split("/")
    if len(parts) != 3:
        raise ValueError
    d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
    if y < 100:
        y += 2000
    return date(y, m, d)


def months_in_range(d_from: date, d_to: date):
    """Llista de (any, mes) que cobreix el rang, inclusiu en els dos extrems."""
    result = []
    y, m = d_from.year, d_from.month
    while (y, m) <= (d_to.year, d_to.month):
        result.append((y, m))
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return result


def month_window(year: int, month: int):
    """(inici_str, fi_exclusiva_str) en format YYYY-MM-DD per a un mes sencer."""
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return str(start), str(end)


# ─── Lògica de descàrrega i filtre ────────────────────────────────────────────

def download_and_filter(client: AdtendeClient, municipio: str, d_from: date, d_to: date) -> pd.DataFrame:
    """
    Descarrega mes a mes (filtre td_managed) i aplica el filtre doble
    (td_managed i td_created dins del rang), comparant com strings.
    """
    s_from = str(d_from)
    s_to   = str(d_to + timedelta(days=1))   # < dia+1, mai <=

    mesos = months_in_range(d_from, d_to)
    dfs = []

    for y, m in mesos:
        m_from, m_to = month_window(y, m)
        filters = [{"type": "date", "variable": "td_managed",
                    "values": {"gte": m_from, "lt": m_to}}]
        try:
            df_m = client.query("tickets_enriquits", filters=filters)
            sub = df_m[
                (df_m["des_client"]  == municipio) &
                (df_m["des_project"] == "OAC 360º")
            ].copy()
            dfs.append(sub)
            print(f"    {y}-{m:02d}  →  {len(sub):>5} tickets")
        except Exception as e:
            print(f"    {y}-{m:02d}  →  ERROR: {e}")

    if not dfs:
        return pd.DataFrame()

    full = pd.concat(dfs, ignore_index=True)

    # Filtre doble: td_managed i td_created dins del rang (comparació com strings)
    df = full[
        (full["td_managed"] >= s_from) & (full["td_managed"] < s_to) &
        (full["td_created"] >= s_from) & (full["td_created"] < s_to)
    ].copy()

    return df


# ─── Càlcul dels 10 indicadors ────────────────────────────────────────────────

def calcular_indicadors(df: pd.DataFrame) -> list[dict]:
    total = len(df)
    if total == 0:
        return [{"Indicador": "Total assistències", "Valor": 0, "Detall": ""}]

    # Població i percentatge
    pop_vals = df["val_population"].dropna()
    pop = float(pop_vals.iloc[0]) if len(pop_vals) > 0 else None
    pct_pop = f"{total / pop * 100:.2f}%" if pop else "N/D"
    pop_str = f"{int(pop):,}".replace(",", ".") if pop else "N/D"

    # Satisfacció (només enquestable + rating no nul)
    enc = df[(df["val_encuestable"] == 1) & (df["val_rating"].notna())]
    n_enc = len(enc)
    sat   = f"{enc['val_rating'].mean():.2f}" if n_enc > 0 else "N/D"
    p1    = f"{enc['val_pregunta1'].mean():.2f}" if n_enc > 0 else "N/D"
    p2    = f"{enc['val_pregunta2'].mean():.2f}" if n_enc > 0 else "N/D"
    p3    = f"{enc['val_pregunta3'].mean():.2f}" if n_enc > 0 else "N/D"

    # Temps mig (val_time_spent és en MINUTS)
    avg_t   = df["val_time_spent"].mean()
    avg_m   = int(avg_t) if pd.notna(avg_t) else 0
    avg_s   = int((avg_t - avg_m) * 60) if pd.notna(avg_t) else 0
    temps   = f"{avg_m}m {avg_s:02d}s"

    # TRUCA'M (per canal, compatible amb dades pre-2022 sense flg_liam)
    trucam = int(df["des_entry_channel"].isin(["TRUCA'M LOCUCIO", "TRUCA'M WEB"]).sum())

    # Franja tarda
    tarda = int((df["flg_morning_schedule"] == "15-24h").sum())

    # Cita prèvia
    cita = int((df["des_category_0"] == "Cita Prèvia").sum())

    # Catàleg de tràmits
    cat_tramits = int(df["des_category_1"].isin(["Catàleg de tràmits", "eTramitador"]).sum())

    # Campanyes puntuals
    campanyes_cats = [
        "Estat dels meus expedients", "Inscripcions", "Processos selectius",
        "eNotificacions", "Signatura electrònica", "Carpeta del Ciutadà",
    ]
    campanyes = int(df["des_category_1"].isin(campanyes_cats).sum())

    # Centraleta
    centraleta = int((df["des_category_1"] == "Trucada per centraleta").sum())

    def pct(n):
        return f"{n / total * 100:.1f}%" if total else "0%"

    return [
        {"Indicador": "Total assistències",   "Valor": total,                                "Detall": ""},
        {"Indicador": "Població (ref.)",       "Valor": pop_str,                              "Detall": ""},
        {"Indicador": "% Població atesa",      "Valor": pct_pop,                              "Detall": ""},
        {"Indicador": "Grau satisfacció /5",   "Valor": sat,                                  "Detall": f"n={n_enc}"},
        {"Indicador": "  · Pregunta 1 /5",     "Valor": p1,                                   "Detall": ""},
        {"Indicador": "  · Pregunta 2 /5",     "Valor": p2,                                   "Detall": ""},
        {"Indicador": "  · Pregunta 3 /5",     "Valor": p3,                                   "Detall": ""},
        {"Indicador": "Temps mig consulta",    "Valor": temps,                                "Detall": ""},
        {"Indicador": "Ús TRUCA'M",            "Valor": trucam,                               "Detall": pct(trucam)},
        {"Indicador": "Franja tarda (15-24h)", "Valor": tarda,                                "Detall": pct(tarda)},
        {"Indicador": "Cita prèvia",           "Valor": cita,                                 "Detall": pct(cita)},
        {"Indicador": "Catàleg de tràmits",    "Valor": cat_tramits,                          "Detall": pct(cat_tramits)},
        {"Indicador": "Campanyes puntuals",    "Valor": campanyes,                            "Detall": pct(campanyes)},
        {"Indicador": "Trucades centraleta",   "Valor": centraleta,                           "Detall": pct(centraleta)},
    ]


# ─── Export Excel ─────────────────────────────────────────────────────────────

def exportar_excel(df_ind: pd.DataFrame, df_raw: pd.DataFrame,
                   municipio: str, d_from: date, d_to: date) -> str:
    safe_name = municipio.replace(" ", "_").replace("/", "-")
    filename  = f"informe_{safe_name}_{d_from.strftime('%Y%m%d')}_{d_to.strftime('%Y%m%d')}.xlsx"

    with pd.ExcelWriter(filename, engine="openpyxl") as writer:
        df_ind.to_excel(writer, sheet_name="Indicadors", index=False)
        df_raw.to_excel(writer, sheet_name="Dades raw",  index=False)

        # Amplada de columnes
        ws = writer.sheets["Indicadors"]
        ws.column_dimensions["A"].width = 32
        ws.column_dimensions["B"].width = 16
        ws.column_dimensions["C"].width = 12

    return filename


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("\n╔══════════════════════════════════════════╗")
    print("║   Extracció dades analítiques — OAC 360  ║")
    print("╚══════════════════════════════════════════╝\n")

    # ── Inputs ──────────────────────────────────────────────────────────────
    municipio = input("Municipi (tal com apareix al BI): ").strip()
    if not municipio:
        print("Error: cal introduir un municipi.")
        sys.exit(1)

    while True:
        try:
            d_from = parse_date(input("Data inici  (DD/MM/AAAA): "))
            break
        except (ValueError, IndexError):
            print("  ↳ Format incorrecte. Exemple: 06/10/2021")

    while True:
        try:
            d_to = parse_date(input("Data fi     (DD/MM/AAAA): "))
            break
        except (ValueError, IndexError):
            print("  ↳ Format incorrecte. Exemple: 06/10/2022")

    if d_to < d_from:
        print("Error: la data fi ha de ser posterior a la data inici.")
        sys.exit(1)

    # ── Descàrrega ──────────────────────────────────────────────────────────
    print(f"\n  Municipi : {municipio}")
    print(f"  Període  : {d_from.strftime('%d/%m/%Y')} → {d_to.strftime('%d/%m/%Y')}")
    print("\n  Descarregant dades...\n")

    client = AdtendeClient()
    client.login()

    df = download_and_filter(client, municipio, d_from, d_to)

    if df.empty:
        print("\n⚠️  No s'han trobat dades. Comprova el nom del municipi.")
        sys.exit(1)

    # ── Càlcul ──────────────────────────────────────────────────────────────
    indicadors = calcular_indicadors(df)
    df_ind = pd.DataFrame(indicadors)

    # ── Mostra resultats ────────────────────────────────────────────────────
    sep = "─" * 52
    print(f"\n  {sep}")
    print(f"  {municipio}  ·  {d_from.strftime('%d/%m/%Y')} → {d_to.strftime('%d/%m/%Y')}")
    print(f"  {sep}")
    for row in indicadors:
        detall = f"  ({row['Detall']})" if row["Detall"] else ""
        print(f"  {row['Indicador']:<32} {str(row['Valor']):>10}{detall}")
    print(f"  {sep}\n")

    # ── Exporta ─────────────────────────────────────────────────────────────
    filename = exportar_excel(df_ind, df, municipio, d_from, d_to)
    print(f"  ✅  Exportat a: {filename}\n")


if __name__ == "__main__":
    main()
