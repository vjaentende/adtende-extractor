#!/usr/bin/env python3
"""
Extracció de dades analítiques per municipi i rang de dates.
Genera dues columnes: Ràtio Ajuntament (municipi concret) i Ràtio General (tots els municipis).

Executa:  python sacar_datos.py
"""

import sys
import calendar
from datetime import date, timedelta

import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

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

def download_and_filter(client: AdtendeClient, d_from: date, d_to: date,
                        municipio: str = None) -> pd.DataFrame:
    """
    Descarrega mes a mes (filtre td_managed) i aplica el filtre doble.
    Si municipio=None, descarrega TOTS els municipis (Ràtio General).
    """
    s_from = str(d_from)
    s_to   = str(d_to + timedelta(days=1))

    mesos = months_in_range(d_from, d_to)
    dfs = []

    label = municipio if municipio else "GENERAL"

    for y, m in mesos:
        m_from, m_to = month_window(y, m)
        filters = [{"type": "date", "variable": "td_managed",
                    "values": {"gte": m_from, "lt": m_to}}]
        try:
            df_m = client.query("tickets_enriquits", filters=filters)
            if municipio:
                sub = df_m[
                    (df_m["des_client"]  == municipio) &
                    (df_m["des_project"] == "OAC 360º")
                ].copy()
            else:
                sub = df_m[df_m["des_project"] == "OAC 360º"].copy()
            dfs.append(sub)
            print(f"    [{label}] {y}-{m:02d}  →  {len(sub):>6} tickets")
        except Exception as e:
            print(f"    [{label}] {y}-{m:02d}  →  ERROR: {e}")

    if not dfs:
        return pd.DataFrame()

    full = pd.concat(dfs, ignore_index=True)

    df = full[
        (full["td_managed"] >= s_from) & (full["td_managed"] < s_to) &
        (full["td_created"] >= s_from) & (full["td_created"] < s_to)
    ].copy()

    return df


# ─── Càlcul dels indicadors ───────────────────────────────────────────────────

def calcular_indicadors(df: pd.DataFrame, es_general: bool = False) -> list[dict]:
    """
    Calcula els indicadors. Si es_general=True, el % Població atesa
    es calcula com la mitjana dels % per municipi (cada municipi té la seva població).
    """
    total = len(df)
    if total == 0:
        return []

    # Satisfacció (només enquestable + rating no nul) — forcem numèric
    for col in ["val_rating", "val_pregunta1", "val_pregunta2", "val_pregunta3", "val_encuestable"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    enc   = df[(df["val_encuestable"] == 1) & (df["val_rating"].notna())]
    n_enc = len(enc)
    sat   = f"{enc['val_rating'].mean():.2f}"    if n_enc > 0 else "N/D"
    p1    = f"{enc['val_pregunta1'].mean():.2f}" if n_enc > 0 else "N/D"
    p2    = f"{enc['val_pregunta2'].mean():.2f}" if n_enc > 0 else "N/D"
    p3    = f"{enc['val_pregunta3'].mean():.2f}" if n_enc > 0 else "N/D"

    # Temps mig (val_time_spent és en MINUTS) — forcem numèric
    df["val_time_spent"] = pd.to_numeric(df["val_time_spent"], errors="coerce")
    avg_t = df["val_time_spent"].mean()
    avg_m = int(avg_t) if pd.notna(avg_t) else 0
    avg_s = int((avg_t - avg_m) * 60) if pd.notna(avg_t) else 0
    temps = f"{avg_m}m {avg_s:02d}s"

    # % Població atesa
    if es_general:
        # Mitjana dels % per municipi (cada un té la seva població de referència)
        pcts = []
        for muni, grp in df.groupby("des_client"):
            pop_vals = grp["val_population"].dropna()
            if len(pop_vals) > 0:
                pop = float(pop_vals.iloc[0])
                if pop > 0:
                    pcts.append(len(grp) / pop * 100)
        pct_pop = f"{sum(pcts)/len(pcts):.2f}%" if pcts else "N/D"
        pop_str = f"{df['des_client'].nunique()} municipis"
    else:
        pop_vals = df["val_population"].dropna()
        pop      = float(pop_vals.iloc[0]) if len(pop_vals) > 0 else None
        pct_pop  = f"{total / pop * 100:.2f}%" if pop else "N/D"
        pop_str  = f"{int(pop):,}".replace(",", ".") if pop else "N/D"

    # TRUCA'M
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
        {"#": "—",  "Indicador": "Total assistències",          "Valor": total,     "Pct": ""},
        {"#": "",   "Indicador": "Població (ref.)",              "Valor": pop_str,   "Pct": ""},
        {"#": "1",  "Indicador": "% Població atesa",             "Valor": pct_pop,   "Pct": ""},
        {"#": "2",  "Indicador": "Grau de satisfacció /5",       "Valor": sat,       "Pct": f"n={n_enc}"},
        {"#": "2.1","Indicador": "  Com valora la qualitat?",    "Valor": p1,        "Pct": ""},
        {"#": "2.1","Indicador": "  Li han resolt la consulta?", "Valor": p2,        "Pct": ""},
        {"#": "2.1","Indicador": "  Com valora el tracte?",      "Valor": p3,        "Pct": ""},
        {"#": "3",  "Indicador": "Temps mig consulta",           "Valor": temps,     "Pct": ""},
        {"#": "4",  "Indicador": "Ús del TRUCA'M",               "Valor": trucam,    "Pct": pct(trucam)},
        {"#": "5",  "Indicador": "Assistències franja tarda",    "Valor": tarda,     "Pct": pct(tarda)},
        {"#": "6",  "Indicador": "Assistències Cita prèvia",     "Valor": cita,      "Pct": pct(cita)},
        {"#": "7",  "Indicador": "Assistències Catàleg tràmits", "Valor": cat_tramits,"Pct": pct(cat_tramits)},
        {"#": "8",  "Indicador": "Ús servei Campanyes puntuals", "Valor": campanyes, "Pct": pct(campanyes)},
        {"#": "10", "Indicador": "Trucades per centraleta",      "Valor": centraleta,"Pct": pct(centraleta)},
    ]


# ─── Export Excel amb dues columnes ──────────────────────────────────────────

def exportar_excel(ind_ajunt: list[dict], ind_general: list[dict],
                   df_raw: pd.DataFrame, municipio: str,
                   d_from: date, d_to: date) -> str:

    safe_name = municipio.replace(" ", "_").replace("/", "-")
    filename  = f"informe_{safe_name}_{d_from.strftime('%Y%m%d')}_{d_to.strftime('%Y%m%d')}.xlsx"

    with pd.ExcelWriter(filename, engine="openpyxl") as writer:

        # ── Full "Indicadors" ────────────────────────────────────────────────
        # Construïm el DataFrame combinat: una fila per indicador, 2 columnes de valor
        rows = []
        gen_map = {r["Indicador"]: r for r in ind_general}
        for r in ind_ajunt:
            gen = gen_map.get(r["Indicador"], {})
            rows.append({
                "#":                r["#"],
                "Indicador":        r["Indicador"],
                "Ràtio Ajuntament": r["Valor"],
                "%":                r["Pct"],
                "Ràtio General":    gen.get("Valor", "N/D"),
                "% General":        gen.get("Pct", ""),
            })

        df_ind = pd.DataFrame(rows)
        df_ind.to_excel(writer, sheet_name="Indicadors", index=False)

        # Estil del full Indicadors
        ws = writer.sheets["Indicadors"]
        _estil_indicadors(ws, municipio, d_from, d_to)

        # ── Full "Dades raw" ─────────────────────────────────────────────────
        df_raw.to_excel(writer, sheet_name="Dades raw", index=False)

    return filename


def _parse_numeric(val) -> float | None:
    """
    Extreu un valor numèric comparable d'un valor formatat.
    Exemples: "3.45" → 3.45 | "12.3%" → 12.3 | "14m 37s" → 14.6 | 1234 → 1234.0
    Retorna None si no és comparable (ex: "N/D", "5 municipis").
    """
    if val is None:
        return None
    s = str(val).strip()
    if s in ("N/D", "", "—"):
        return None
    # Percentatge: "12.3%"
    if s.endswith("%"):
        try:
            return float(s[:-1].replace(",", "."))
        except ValueError:
            return None
    # Temps: "14m 37s"
    if "m" in s and "s" in s:
        try:
            parts = s.replace("s", "").split("m")
            return float(parts[0]) + float(parts[1]) / 60
        except (ValueError, IndexError):
            return None
    # Número pur (pot tenir punts de milers: "1.234")
    try:
        return float(s.replace(".", "").replace(",", "."))
    except ValueError:
        return None


# Indicadors on MENOR valor és millor:
# - Temps mig consulta: menys temps = més eficient
# - Catàleg de tràmits: menys = la gent sap fer els tràmits sola
# - Cita prèvia: menys = menys càrrega presencial
# - Trucades centraleta: menys = menys derivacions, més autonomia
INDICADORS_INVERTITS = {
    "Temps mig consulta",
    "Assistències Catàleg tràmits",
    "Assistències Cita prèvia",
    "Trucades per centraleta",
}


def _estil_indicadors(ws, municipio: str, d_from: date, d_to: date):
    """Aplica estil professional al full Indicadors amb vermell/verd per comparació."""
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    COLOR_HEADER  = "1B3A6B"
    COLOR_AJUNT   = "00B4A6"
    COLOR_GENERAL = "4A90D9"
    COLOR_FILA_ALT= "F2F8FF"
    COLOR_SUBIND  = "F7F7F7"
    WHITE         = "FFFFFF"
    GREEN         = "1A7A1A"   # verd fosc per text
    RED           = "C0392B"   # vermell per text
    GREEN_BG      = "E8F5E9"   # fons verd clar
    RED_BG        = "FFEBEE"   # fons vermell clar

    thin   = Side(style="thin", color="CCCCCC")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    # Amplades
    col_widths = [4, 36, 18, 10, 18, 10]
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # Capçalera (fila 1)
    headers = ["#", "Indicador",
               f"Ràtio {municipio}", "%",
               "Ràtio General", "% General"]
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font      = Font(bold=True, color=WHITE, size=10)
        cell.fill      = PatternFill("solid", fgColor=COLOR_HEADER)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border    = border
    ws.row_dimensions[1].height = 30

    ws.cell(row=1, column=3).fill = PatternFill("solid", fgColor=COLOR_AJUNT)
    ws.cell(row=1, column=4).fill = PatternFill("solid", fgColor=COLOR_AJUNT)
    ws.cell(row=1, column=5).fill = PatternFill("solid", fgColor=COLOR_GENERAL)
    ws.cell(row=1, column=6).fill = PatternFill("solid", fgColor=COLOR_GENERAL)

    # Files de dades
    for row_idx in range(2, ws.max_row + 1):
        num_val  = str(ws.cell(row=row_idx, column=1).value or "")
        ind_val  = str(ws.cell(row=row_idx, column=2).value or "")
        is_sub   = num_val == "2.1"
        is_total = num_val == "—"
        is_alt   = (row_idx % 2 == 0)

        # Compara Ràtio Ajuntament (col 3) vs Ràtio General (col 5)
        val_ajunt   = _parse_numeric(ws.cell(row=row_idx, column=3).value)
        val_general = _parse_numeric(ws.cell(row=row_idx, column=5).value)
        invertit    = ind_val.strip() in INDICADORS_INVERTITS

        color_text = None
        color_bg   = None
        if val_ajunt is not None and val_general is not None and not is_total:
            if val_ajunt > val_general:
                color_text = RED   if invertit else GREEN
                color_bg   = RED_BG if invertit else GREEN_BG
            elif val_ajunt < val_general:
                color_text = GREEN if invertit else RED
                color_bg   = GREEN_BG if invertit else RED_BG

        bg_default = COLOR_SUBIND if is_sub else (COLOR_FILA_ALT if is_alt else WHITE)

        for col in range(1, 7):
            cell = ws.cell(row=row_idx, column=col)
            cell.border    = border
            cell.alignment = Alignment(
                vertical="center",
                horizontal="center" if col != 2 else "left",
                indent=1 if col == 2 and is_sub else 0
            )

            # Color vermell/verd només a les columnes de valor de l'ajuntament (3 i 4)
            if col in (3, 4) and color_text and not is_sub:
                cell.fill = PatternFill("solid", fgColor=color_bg)
                cell.font = Font(
                    bold=is_total, italic=is_sub, size=9 if is_sub else 10,
                    color=color_text
                )
            else:
                cell.fill = PatternFill("solid", fgColor=bg_default)
                if is_total:
                    cell.font = Font(bold=True, size=10)
                elif is_sub:
                    cell.font = Font(italic=True, color="666666", size=9)
                else:
                    cell.font = Font(size=10)

        ws.row_dimensions[row_idx].height = 18

    ws.freeze_panes = "A2"


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("\n╔══════════════════════════════════════════════════════╗")
    print("║     Extracció dades analítiques — OAC 360            ║")
    print("║     Ràtio Ajuntament + Ràtio General                 ║")
    print("╚══════════════════════════════════════════════════════╝\n")

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

    print(f"\n  Municipi : {municipio}")
    print(f"  Període  : {d_from.strftime('%d/%m/%Y')} → {d_to.strftime('%d/%m/%Y')}")

    client = AdtendeClient()
    client.login()

    # ── Descàrrega Ajuntament ────────────────────────────────────────────────
    print(f"\n  Descarregant dades del municipi...\n")
    df_ajunt = download_and_filter(client, d_from, d_to, municipio=municipio)

    if df_ajunt.empty:
        print("\n⚠️  No s'han trobat dades. Comprova el nom del municipi.")
        sys.exit(1)

    # ── Descàrrega General ───────────────────────────────────────────────────
    print(f"\n  Descarregant dades generals (tots els municipis)...\n")
    df_general = download_and_filter(client, d_from, d_to, municipio=None)

    # ── Càlcul ──────────────────────────────────────────────────────────────
    ind_ajunt   = calcular_indicadors(df_ajunt,   es_general=False)
    ind_general = calcular_indicadors(df_general, es_general=True)

    # ── Mostra resultats ────────────────────────────────────────────────────
    sep = "─" * 72
    print(f"\n  {sep}")
    print(f"  {'Indicador':<32} {'Ajuntament':>14}  {'General':>14}")
    print(f"  {sep}")
    gen_map = {r["Indicador"]: r for r in ind_general}
    for r in ind_ajunt:
        gen = gen_map.get(r["Indicador"], {})
        val_a = f"{r['Valor']} {r['Pct']}".strip()
        val_g = f"{gen.get('Valor','N/D')} {gen.get('Pct','')}".strip()
        print(f"  {r['Indicador']:<32} {val_a:>14}  {val_g:>14}")
    print(f"  {sep}\n")

    # ── Exporta ─────────────────────────────────────────────────────────────
    filename = exportar_excel(ind_ajunt, ind_general, df_ajunt, municipio, d_from, d_to)
    print(f"  ✅  Exportat a: {filename}\n")


if __name__ == "__main__":
    main()
