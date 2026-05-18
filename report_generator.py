"""
Generador d'informes mensuals — Adtende Analytics
"""

import io
import calendar
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, HRFlowable, KeepTogether,
)

from api_client import AdtendeClient


# ── Paleta ───────────────────────────────────────────────────────────────────
C_NAVY    = "#1B3A6B"
C_TEAL    = "#00B4A6"
C_AMBER   = "#F4A620"
C_RED     = "#E05A5A"
C_LIGHT   = "#F4F7FB"
C_MID     = "#DDE6F0"
C_TEXT    = "#2C2C2C"
C_MUTED   = "#7A8FA6"
C_WHITE   = "#FFFFFF"

RL_NAVY   = colors.HexColor(C_NAVY)
RL_TEAL   = colors.HexColor(C_TEAL)
RL_AMBER  = colors.HexColor(C_AMBER)
RL_LIGHT  = colors.HexColor(C_LIGHT)
RL_MID    = colors.HexColor(C_MID)
RL_TEXT   = colors.HexColor(C_TEXT)
RL_MUTED  = colors.HexColor(C_MUTED)

CHART_COLORS = [C_NAVY, C_TEAL, C_AMBER, C_RED, "#7B68EE", "#52C784", "#F47560", "#97BBD5"]

MESOS = {
    1:"Gener", 2:"Febrer", 3:"Març", 4:"Abril",
    5:"Maig", 6:"Juny", 7:"Juliol", 8:"Agost",
    9:"Setembre", 10:"Octubre", 11:"Novembre", 12:"Desembre",
}
DIES = ["Dilluns","Dimarts","Dimecres","Dijous","Divendres","Dissabte","Diumenge"]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _fmt(n):
    if n is None: return "—"
    if isinstance(n, float):
        return f"{n:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{int(n):,}".replace(",", ".")

def _pct(a, b): return round(a / b * 100, 1) if b else 0.0

def _fmt_time(minutes):
    """Converteix minuts a format 'Xm Ys'."""
    if minutes is None: return "—"
    total_s = round(minutes * 60)
    m, s = divmod(total_s, 60)
    return f"{m}m {s:02d}s"

def _buf(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf

def _mpl_style():
    plt.rcParams.update({
        "font.family": "sans-serif",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "axes.grid": True,
        "grid.color": "#DDE6F0",
        "grid.linewidth": 0.6,
        "axes.axisbelow": True,
        "xtick.color": C_MUTED,
        "ytick.color": C_MUTED,
        "axes.labelcolor": C_MUTED,
        "figure.facecolor": "white",
    })


# ── Estilos ──────────────────────────────────────────────────────────────────

def _S():
    s = {}
    def ps(name, **kw): return ParagraphStyle(name, **kw)
    s["cover_title"]   = ps("ct", fontSize=34, textColor=colors.white, fontName="Helvetica-Bold",
                              alignment=TA_CENTER, leading=40, spaceAfter=8)
    s["cover_period"]  = ps("cp", fontSize=16, textColor=colors.HexColor("#A8C8E8"),
                              fontName="Helvetica", alignment=TA_CENTER, leading=22)
    s["cover_meta"]    = ps("cm", fontSize=9,  textColor=colors.HexColor("#6A90B8"),
                              fontName="Helvetica", alignment=TA_CENTER)
    s["sec_title"]     = ps("st", fontSize=12, textColor=RL_NAVY, fontName="Helvetica-Bold",
                              spaceBefore=16, spaceAfter=5, leading=16)
    s["body"]          = ps("bd", fontSize=9,  textColor=RL_TEXT, fontName="Helvetica",
                              leading=14, spaceAfter=4)
    s["body_muted"]    = ps("bm", fontSize=8,  textColor=RL_MUTED, fontName="Helvetica",
                              leading=12)
    s["kpi_val"]       = ps("kv", fontSize=17, textColor=RL_NAVY, fontName="Helvetica-Bold",
                              alignment=TA_CENTER, leading=20)
    s["kpi_lbl"]       = ps("kl", fontSize=7.5, textColor=RL_MUTED, fontName="Helvetica",
                              alignment=TA_CENTER, leading=10)
    s["th"]            = ps("th", fontSize=8,  textColor=colors.white, fontName="Helvetica-Bold",
                              alignment=TA_CENTER)
    s["td_l"]          = ps("tdl", fontSize=8, textColor=RL_TEXT,  fontName="Helvetica", alignment=TA_LEFT)
    s["td_c"]          = ps("tdc", fontSize=8, textColor=RL_TEXT,  fontName="Helvetica", alignment=TA_CENTER)
    s["td_r"]          = ps("tdr", fontSize=8, textColor=RL_TEXT,  fontName="Helvetica", alignment=TA_RIGHT)
    s["td_bold"]       = ps("tdb", fontSize=8, textColor=RL_NAVY,  fontName="Helvetica-Bold", alignment=TA_RIGHT)
    s["highlight"]     = ps("hl", fontSize=9,  textColor=RL_TEAL,  fontName="Helvetica-Bold")
    return s


# ── Components de layout ─────────────────────────────────────────────────────

def _kpi_cards(kpis, S):
    """
    kpis = [(valor_str, label, color_accent), ...]
    Retorna una taula d'una fila amb targetes KPI.
    """
    W = A4[0] - 3*cm
    n = len(kpis)
    cw = W / n

    val_row = []
    lbl_row = []
    for val, lbl, _ in kpis:
        val_row.append(Paragraph(val, S["kpi_val"]))
        lbl_row.append(Paragraph(lbl, S["kpi_lbl"]))

    t = Table([val_row, lbl_row], colWidths=[cw]*n, rowHeights=[None, 14])
    style = [
        ("BACKGROUND",    (0,0), (-1,-1), RL_LIGHT),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("RIGHTPADDING",  (0,0), (-1,-1), 6),
        ("LINEBELOW",     (0,0), (-1,0),  2, RL_TEAL),
        ("LINEBEFORE",    (1,0), (-1,-1), 0.5, RL_MID),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]
    t.setStyle(TableStyle(style))
    return t


def _data_table(headers, rows, S, col_widths=None, alignments=None, total_row=False):
    W = A4[0] - 3*cm
    n = len(headers)
    if col_widths is None:
        col_widths = [W/n]*n
    if alignments is None:
        alignments = ["l"] + ["r"]*(n-1)

    style_map = {"l": S["td_l"], "c": S["td_c"], "r": S["td_r"]}

    header_cells = [Paragraph(h, S["th"]) for h in headers]
    data = [header_cells]
    for i, row in enumerate(rows):
        is_last = total_row and i == len(rows)-1
        st = S["td_bold"] if is_last else None
        cells = []
        for j, cell in enumerate(row):
            base = style_map[alignments[j]]
            cells.append(Paragraph(str(cell), st or base))
        data.append(cells)

    t = Table(data, colWidths=col_widths, repeatRows=1)
    ts = [
        ("BACKGROUND",    (0,0),  (-1,0),  RL_NAVY),
        ("ROWBACKGROUNDS",(0,1),  (-1,-1), [colors.white, RL_LIGHT]),
        ("GRID",          (0,0),  (-1,-1), 0.25, RL_MID),
        ("TOPPADDING",    (0,0),  (-1,-1), 5),
        ("BOTTOMPADDING", (0,0),  (-1,-1), 5),
        ("LEFTPADDING",   (0,0),  (-1,-1), 7),
        ("RIGHTPADDING",  (0,0),  (-1,-1), 7),
        ("VALIGN",        (0,0),  (-1,-1), "MIDDLE"),
    ]
    if total_row and len(rows) > 0:
        ts += [
            ("BACKGROUND",  (0,-1), (-1,-1), colors.HexColor("#EBF4FF")),
            ("LINEABOVE",   (0,-1), (-1,-1), 1, RL_TEAL),
        ]
    t.setStyle(TableStyle(ts))
    return t


def _section_header(num, title, S):
    badge_data = [[Paragraph(f"<b>{num}</b>", ParagraphStyle(
        "badge", fontSize=9, textColor=colors.white, fontName="Helvetica-Bold",
        alignment=TA_CENTER))]]
    badge = Table(badge_data, colWidths=[0.6*cm], rowHeights=[0.6*cm])
    badge.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), RL_TEAL),
        ("TOPPADDING", (0,0), (-1,-1), 1),
        ("BOTTOMPADDING", (0,0), (-1,-1), 1),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    title_para = Paragraph(title, S["sec_title"])
    row = Table([[badge, title_para]], colWidths=[0.8*cm, A4[0]-3.8*cm],
                rowHeights=[0.6*cm])
    row.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))
    return [
        Spacer(1, 0.5*cm),
        HRFlowable(width="100%", thickness=0.5, color=RL_MID, spaceAfter=4),
        row,
        Spacer(1, 0.2*cm),
    ]


# ── Gràfiques ─────────────────────────────────────────────────────────────────

def _chart_heatmap(df):
    if "td_created" not in df.columns or "th_created" not in df.columns:
        return None
    _mpl_style()
    d = df.copy()
    d["td_created"] = pd.to_datetime(d["td_created"], errors="coerce")
    d["dia"] = d["td_created"].dt.dayofweek
    d["hora"] = pd.to_datetime(d["th_created"], format="%H:%M:%S", errors="coerce").dt.hour
    pivot = d.groupby(["dia","hora"]).size().unstack(fill_value=0)\
             .reindex(index=range(7), columns=range(24), fill_value=0)

    fig, ax = plt.subplots(figsize=(12, 3.6))
    im = ax.imshow(pivot.values, aspect="auto", cmap="Blues", interpolation="nearest")

    ax.set_xticks(range(24))
    ax.set_xticklabels([f"{h:02d}h" for h in range(24)], fontsize=6.5)
    ax.set_yticks(range(7))
    ax.set_yticklabels(DIES, fontsize=8)
    ax.tick_params(length=0)
    ax.set_xlabel("Hora del dia", fontsize=8)
    ax.grid(False)

    mx = pivot.values.max()
    for i in range(7):
        for j in range(24):
            v = pivot.values[i, j]
            if v > 0:
                c = "white" if v > mx * 0.55 else C_NAVY
                ax.text(j, i, str(v), ha="center", va="center", fontsize=5.5, color=c, fontweight="bold")

    cbar = fig.colorbar(im, ax=ax, shrink=0.8, pad=0.01)
    cbar.ax.tick_params(labelsize=7, colors=C_MUTED)
    cbar.outline.set_visible(False)
    fig.tight_layout(pad=0.5)
    return _buf(fig)


def _chart_hbars(series, total, title="", color=C_NAVY, top_n=12):
    _mpl_style()
    s = series.head(top_n)
    fig, ax = plt.subplots(figsize=(9, max(3, len(s)*0.52)))

    y = range(len(s))
    bars = ax.barh(list(y), s.values[::-1] if True else s.values,
                   color=color, height=0.55, left=0)
    # ordre descendent
    s_sorted = s.sort_values(ascending=True)
    bars = ax.barh(range(len(s_sorted)), s_sorted.values, color=color, height=0.55)

    ax.set_yticks(range(len(s_sorted)))
    ax.set_yticklabels(s_sorted.index, fontsize=8)
    ax.set_xlabel("Consultes", fontsize=8)
    ax.spines["bottom"].set_color(C_MID)
    ax.set_xlim(0, s_sorted.values.max() * 1.22)

    for bar, val in zip(bars, s_sorted.values):
        pct = _pct(val, total)
        ax.text(bar.get_width() + s_sorted.values.max()*0.01,
                bar.get_y() + bar.get_height()/2,
                f"{_fmt(val)}  ({pct}%)", va="center", fontsize=7.5, color=C_TEXT)

    fig.tight_layout(pad=0.5)
    return _buf(fig)


def _chart_canal(series, total):
    _mpl_style()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 3.8),
                                    gridspec_kw={"width_ratios": [1, 1.4]})

    # Donut
    colors_list = CHART_COLORS[:len(series)]
    wedges, _, autotexts = ax1.pie(
        series.values, autopct="%1.1f%%", colors=colors_list,
        startangle=90, pctdistance=0.72,
        wedgeprops={"edgecolor": "white", "linewidth": 2},
    )
    for at in autotexts:
        at.set_fontsize(8)
        at.set_color("white")
        at.set_fontweight("bold")
    centre = plt.Circle((0,0), 0.45, color="white")
    ax1.add_patch(centre)
    ax1.text(0, 0, _fmt(total), ha="center", va="center",
             fontsize=13, fontweight="bold", color=C_NAVY)
    ax1.text(0, -0.18, "total", ha="center", va="center",
             fontsize=7, color=C_MUTED)
    ax1.set_aspect("equal")
    ax1.axis("off")

    # Barres horitzontals
    s = series.sort_values(ascending=True)
    bars = ax2.barh(range(len(s)), s.values,
                    color=CHART_COLORS[:len(s)], height=0.55)
    ax2.set_yticks(range(len(s)))
    ax2.set_yticklabels(s.index, fontsize=8)
    ax2.set_xlabel("Consultes", fontsize=8)
    ax2.spines["bottom"].set_color(C_MID)
    ax2.set_xlim(0, s.values.max() * 1.3)
    for bar, val in zip(bars, s.values):
        ax2.text(bar.get_width() + s.values.max()*0.01,
                 bar.get_y() + bar.get_height()/2,
                 f"{_fmt(val)}  ({_pct(val,total)}%)",
                 va="center", fontsize=7.5, color=C_TEXT)
    ax2.grid(axis="x")
    ax2.spines["left"].set_visible(False)
    ax2.tick_params(left=False)

    fig.tight_layout(pad=0.8)
    return _buf(fig)


def _chart_evolucion(df):
    if "td_created" not in df.columns:
        return None
    _mpl_style()
    d = df.copy()
    d["td_created"] = pd.to_datetime(d["td_created"], errors="coerce")
    serie = d.groupby("td_created").size().reset_index(name="n").sort_values("td_created")

    fig, ax = plt.subplots(figsize=(10, 3))
    ax.fill_between(serie["td_created"], serie["n"], alpha=0.12, color=C_NAVY)
    ax.plot(serie["td_created"], serie["n"], color=C_NAVY, linewidth=2,
            marker="o", markersize=3.5, markerfacecolor=C_TEAL, markeredgecolor="white",
            markeredgewidth=0.8)
    # Línia de mitjana
    mean_val = serie["n"].mean()
    ax.axhline(mean_val, color=C_TEAL, linewidth=1.2, linestyle="--", alpha=0.7,
               label=f"Mitjana: {mean_val:.0f}")
    ax.legend(fontsize=8, frameon=False, loc="upper right")
    ax.set_ylabel("Consultes / dia", fontsize=8)
    ax.spines["bottom"].set_color(C_MID)
    ax.tick_params(labelsize=7.5)
    fig.tight_layout(pad=0.5)
    return _buf(fig)


def _chart_temps(df):
    col = "val_hours_resolution" if "val_hours_resolution" in df.columns else None
    if col is None:
        return None
    _mpl_style()
    serie = pd.to_numeric(df[col], errors="coerce").dropna() * 60
    if len(serie) == 0:
        return None
    clip = np.percentile(serie, 95)
    serie_c = serie.clip(upper=clip)

    fig, ax = plt.subplots(figsize=(9, 3.2))
    n, bins, patches_list = ax.hist(serie_c, bins=35, color=C_NAVY,
                                     edgecolor="white", linewidth=0.4, alpha=0.85)
    # Color gradient per bins
    for p, v in zip(patches_list, n):
        p.set_facecolor(C_TEAL if v == n.max() else C_NAVY)
        p.set_alpha(0.7 + 0.3*(v/n.max()))

    mean_val = serie.mean()
    median_val = serie.median()
    ax.axvline(mean_val, color=C_AMBER, linewidth=2, linestyle="-",
               label=f"Mitjana: {mean_val:.1f} min")
    ax.axvline(median_val, color=C_TEAL, linewidth=2, linestyle="--",
               label=f"Mediana: {median_val:.1f} min")
    ax.set_xlabel("Minuts per consulta", fontsize=8)
    ax.set_ylabel("Freqüència", fontsize=8)
    ax.legend(fontsize=8, frameon=False)
    ax.tick_params(labelsize=7.5)
    ax.spines["bottom"].set_color(C_MID)
    note = f"* Truncat al P95 ({clip:.0f} min)"
    ax.text(0.99, 0.97, note, transform=ax.transAxes, fontsize=6.5,
            color=C_MUTED, ha="right", va="top")
    fig.tight_layout(pad=0.5)
    return _buf(fig)


def _chart_satisfaccio(df):
    """Gràfic 2-panells: distribució estreles + puntuació per preguntes."""
    col_enc = "val_media_enc"
    q_cols   = ["val_pregunta1", "val_pregunta2", "val_pregunta3"]
    q_labels = ["Pregunta 1", "Pregunta 2", "Pregunta 3"]

    enc = pd.to_numeric(df.get(col_enc, pd.Series(dtype=float)), errors="coerce").dropna()
    q_means, q_ns = [], []
    for c in q_cols:
        s = pd.to_numeric(df.get(c, pd.Series(dtype=float)), errors="coerce").dropna()
        q_means.append(round(s.mean(), 2) if len(s) else None)
        q_ns.append(len(s))

    has_enc = len(enc) > 0
    has_q   = any(m is not None for m in q_means)
    if not has_enc and not has_q:
        return None

    fig, axes = plt.subplots(1, 2, figsize=(13, 3.5))
    fig.patch.set_facecolor("white")

    ax = axes[0]
    if has_enc:
        dist = enc.value_counts().reindex([5, 4, 3, 2, 1], fill_value=0)
        bar_colors = [C_TEAL if v == dist.max() else C_NAVY for v in dist.values]
        bars = ax.barh([f"{'★'*int(k)}" for k in dist.index], dist.values,
                       color=bar_colors, alpha=0.85, height=0.6)
        for bar, val in zip(bars, dist.values):
            ax.text(bar.get_width() + dist.max()*0.01, bar.get_y() + bar.get_height()/2,
                    f"{int(val)}", va="center", fontsize=8, color=C_TEXT)
        ax.set_xlabel("Enquestes", fontsize=8)
        ax.set_title(f"Distribució de Valoracions  (n={len(enc)})", fontsize=9,
                     fontweight="bold", color=C_NAVY, pad=6)
    else:
        ax.text(0.5, 0.5, "Sense dades", ha="center", va="center",
                transform=ax.transAxes, color=C_MUTED, fontsize=10)
    for sp in ["top", "right"]:
        ax.spines[sp].set_visible(False)
    ax.tick_params(labelsize=8)

    ax2 = axes[1]
    if has_q:
        valid = [(lbl, m, n) for lbl, m, n in zip(q_labels, q_means, q_ns) if m is not None]
        lbls, means, ns = zip(*valid) if valid else ([], [], [])
        y = range(len(lbls))
        ax2.barh(list(y), means, color=C_AMBER, alpha=0.85, height=0.5)
        ax2.set_xlim(0, 5.8)
        ax2.axvline(5, color=C_MID, linewidth=0.8, linestyle="--")
        for i, (m, n) in enumerate(zip(means, ns)):
            ax2.text(m + 0.08, i, f"{m:.2f}  (n={n})", va="center", fontsize=8, color=C_TEXT)
        ax2.set_yticks(list(y))
        ax2.set_yticklabels(lbls, fontsize=8)
        ax2.set_xlabel("Puntuació mitjana (1–5)", fontsize=8)
        ax2.set_title("Puntuació per Preguntes", fontsize=9,
                      fontweight="bold", color=C_NAVY, pad=6)
    else:
        ax2.text(0.5, 0.5, "Sense dades", ha="center", va="center",
                 transform=ax2.transAxes, color=C_MUTED, fontsize=10)
    for sp in ["top", "right"]:
        ax2.spines[sp].set_visible(False)
    ax2.tick_params(labelsize=8)

    fig.tight_layout(pad=0.8)
    return _buf(fig)


# ── Page callbacks ────────────────────────────────────────────────────────────

def _callbacks(periode, generated):
    def cover(canvas, doc):
        w, h = A4
        canvas.saveState()
        # Fons blau 65%
        canvas.setFillColor(RL_NAVY)
        canvas.rect(0, h*0.35, w, h*0.65, fill=1, stroke=0)
        # Fons blanc baix
        canvas.setFillColor(colors.white)
        canvas.rect(0, 0, w, h*0.35, fill=1, stroke=0)
        # Banda teal inferior
        canvas.setFillColor(RL_TEAL)
        canvas.rect(0, 0, w, 0.8*cm, fill=1, stroke=0)
        # Línia decorativa teal
        canvas.setStrokeColor(RL_TEAL)
        canvas.setLineWidth(2)
        canvas.line(2*cm, h*0.35 + 0.3*cm, w-2*cm, h*0.35 + 0.3*cm)
        # Quadrat decoratiu top-right
        canvas.setFillColor(colors.HexColor("#152D54"))
        canvas.rect(w-3*cm, h-3*cm, 3*cm, 3*cm, fill=1, stroke=0)
        canvas.setFillColor(RL_TEAL)
        canvas.rect(w-1.5*cm, h-1.5*cm, 1.5*cm, 1.5*cm, fill=1, stroke=0)
        canvas.restoreState()

    def pages(canvas, doc):
        w, h = A4
        canvas.saveState()
        # Header
        canvas.setFillColor(RL_NAVY)
        canvas.rect(0, h-1.1*cm, w, 1.1*cm, fill=1, stroke=0)
        canvas.setFillColor(RL_TEAL)
        canvas.rect(0, h-1.1*cm, 0.5*cm, 1.1*cm, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawString(0.8*cm, h-0.72*cm, "Adtende Analytics")
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(w-1.2*cm, h-0.72*cm, f"Informe — {periode}")
        # Footer
        canvas.setFillColor(colors.HexColor("#F0F4F8"))
        canvas.rect(0, 0, w, 1*cm, fill=1, stroke=0)
        canvas.setFillColor(RL_TEAL)
        canvas.rect(0, 0, 0.3*cm, 1*cm, fill=1, stroke=0)
        canvas.setFillColor(RL_MUTED)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(0.8*cm, 0.38*cm, f"Generat el {generated} · Prenomics / Adtende")
        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(RL_NAVY)
        canvas.drawRightString(w-1*cm, 0.35*cm, f"{doc.page}")
        canvas.restoreState()

    return cover, pages


# ── PDF builder ───────────────────────────────────────────────────────────────

def _build_pdf(df, year, month, periode_label, output_path):
    S = _S()
    generated = date.today().strftime("%d/%m/%Y")
    on_cover, on_pages = _callbacks(periode_label, generated)

    doc = SimpleDocTemplate(
        str(output_path), pagesize=A4,
        leftMargin=1.5*cm, rightMargin=1.5*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm,
        title=f"Informe {periode_label}",
        author="Adtende Analytics",
    )

    story = []
    total = len(df)

    # ── PORTADA ───────────────────────────────────────────────────────────────
    story.append(Spacer(1, 4.5*cm))
    story.append(Paragraph("Informe Mensual<br/>de Consultes", S["cover_title"]))
    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph(periode_label, S["cover_period"]))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(f"OAC 360º · Adtende Analytics", S["cover_meta"]))
    story.append(Spacer(1, 3.8*cm))
    story.append(Paragraph(f"Generat el {generated}", S["cover_meta"]))
    story.append(PageBreak())

    # ── Calcular mètriques ────────────────────────────────────────────────────
    avg_rating, n_rat = None, 0
    if "val_rating" in df.columns:
        r = pd.to_numeric(df["val_rating"], errors="coerce").dropna()
        n_rat = len(r)
        if n_rat: avg_rating = round(r.mean(), 2)

    avg_min = None
    if "val_hours_resolution" in df.columns:
        mask_enc = pd.to_numeric(df.get("val_encuestable", pd.Series(1, index=df.index)),
                                 errors="coerce") == 1
        t = pd.to_numeric(df.loc[mask_enc, "val_hours_resolution"], errors="coerce").dropna()
        if len(t): avg_min = t.mean() * 60

    flg_res = None
    if "flg_resolution" in df.columns:
        res = pd.to_numeric(df["flg_resolution"], errors="coerce")
        flg_res = round(res.sum() / len(res) * 100, 1) if len(res) else None

    n_cats = df["des_category_0"].nunique() if "des_category_0" in df.columns else 0
    n_canals = df["des_entry_channel"].nunique() if "des_entry_channel" in df.columns else 0

    # ── KPIs ─────────────────────────────────────────────────────────────────
    kpis = [(_fmt(total), "Total Consultes", C_NAVY)]
    if flg_res is not None:
        kpis.append((f"{str(flg_res).replace('.',',')}%", "Ratio Resolució", C_TEAL))
    if avg_min is not None:
        kpis.append((_fmt_time(avg_min), "Temps Resolució", C_AMBER))
    if avg_rating is not None:
        kpis.append((f"{avg_rating:.2f}".replace(".",","), "Valoració Mitjana", C_TEAL))
    kpis.append((_fmt(n_cats), "Categories", C_NAVY))
    kpis.append((_fmt(n_canals), "Canals", C_NAVY))

    story.append(Spacer(1, 0.2*cm))
    story.append(_kpi_cards(kpis, S))
    story.append(Spacer(1, 0.3*cm))

    # ── SECCIÓ 1: Evolució diària ─────────────────────────────────────────────
    import calendar as _cal
    story += _section_header("1", "Evolució Diària de Consultes", S)
    _date_col = "td_managed" if "td_managed" in df.columns else "td_created"
    dias = df.groupby(pd.to_datetime(df[_date_col], errors="coerce").dt.date).size()
    dies_mes = _cal.monthrange(year, month)[1]
    max_dia = int(dias.max()) if len(dias) else 0
    min_dia = int(dias.min()) if len(dias) else 0
    story.append(Paragraph(
        f"Al llarg del mes es van registrar <b>{_fmt(total)} consultes</b> en <b>{dies_mes}</b> dies. "
        f"El dia de major activitat va tenir <b>{_fmt(max_dia)}</b> consultes "
        f"i el de menor activitat <b>{_fmt(min_dia)}</b>.",
        S["body"]))
    story.append(Spacer(1, 0.3*cm))
    chart = _chart_evolucion(df)
    if chart:
        story.append(Image(chart, width=16.5*cm, height=5*cm))

    # ── SECCIÓ 2: Distribució per Dia Setmana i Hora ──────────────────────────
    story += _section_header("2", "Distribució per Dia Setmana i Hora", S)
    story.append(Paragraph(
        "El mapa de calor mostra la concentració de consultes per cada combinació "
        "de dia de la setmana i hora del dia. Les cel·les més fosques indiquen major activitat.",
        S["body"]))
    story.append(Spacer(1, 0.3*cm))
    chart = _chart_heatmap(df)
    if chart:
        story.append(Image(chart, width=17*cm, height=6*cm))

    # Taula resum dies
    if "td_created" in df.columns:
        df2 = df.copy()
        df2["td_created"] = pd.to_datetime(df2["td_created"], errors="coerce")
        df2["dia_num"] = df2["td_created"].dt.dayofweek
        per_dia = df2.groupby("dia_num").size().reindex(range(7), fill_value=0)
        story.append(Spacer(1, 0.4*cm))
        rows_dia = [[DIES[i], _fmt(v), f"{_pct(v,total)}%"] for i,v in per_dia.items()]
        rows_dia.append(["TOTAL", _fmt(total), "100%"])
        story.append(_data_table(
            ["Dia", "Consultes", "% Total"], rows_dia, S,
            col_widths=[7*cm, 4*cm, 4*cm],
            alignments=["l","r","r"], total_row=True
        ))

    # ── SECCIÓ 3: Distribució per Categoria ──────────────────────────────────
    story += _section_header("3", "Distribució per Categoria de Consultes", S)
    if "des_category_0" in df.columns:
        cats = df["des_category_0"].value_counts()
        top = cats.index[0]
        story.append(Paragraph(
            f"S'han identificat <b>{n_cats} categories</b>. "
            f"La més freqüent és <b>{top}</b> amb {_fmt(cats.iloc[0])} consultes "
            f"({_pct(cats.iloc[0], total)}% del total).",
            S["body"]))
        story.append(Spacer(1, 0.3*cm))
        chart = _chart_hbars(cats, total, color=C_NAVY)
        if chart:
            story.append(Image(chart, width=17*cm, height=max(4, min(10, len(cats.head(12))*0.6))*cm))
        story.append(Spacer(1, 0.3*cm))
        rows_cat = [[cat, _fmt(cnt), f"{_pct(cnt,total)}%"] for cat,cnt in cats.items()]
        rows_cat.append(["TOTAL", _fmt(total), "100%"])
        story.append(_data_table(
            ["Categoria", "Consultes", "% Total"], rows_cat, S,
            col_widths=[10*cm, 3.5*cm, 3.5*cm],
            alignments=["l","r","r"], total_row=True
        ))

    # ── SECCIÓ 4: Canal d'Assistència ────────────────────────────────────────
    story += _section_header("4", "Distribució per Canal d'Assistència", S)
    if "des_entry_channel" in df.columns:
        canals = df["des_entry_channel"].value_counts()
        story.append(Paragraph(
            f"Les consultes s'han atès a través de <b>{n_canals} canals</b>. "
            f"El canal principal és <b>{canals.index[0]}</b> "
            f"amb el {_pct(canals.iloc[0], total)}% del total.",
            S["body"]))
        story.append(Spacer(1, 0.3*cm))
        chart = _chart_canal(canals, total)
        if chart:
            story.append(Image(chart, width=17*cm, height=5.5*cm))
        story.append(Spacer(1, 0.3*cm))
        rows_can = [[c, _fmt(v), f"{_pct(v,total)}%"] for c,v in canals.items()]
        rows_can.append(["TOTAL", _fmt(total), "100%"])
        story.append(_data_table(
            ["Canal", "Consultes", "% Total"], rows_can, S,
            col_widths=[10*cm, 3.5*cm, 3.5*cm],
            alignments=["l","r","r"], total_row=True
        ))

    # ── SECCIÓ 5: Temps de Resolució ─────────────────────────────────────────
    story += _section_header("5", "Temps de Resolució", S)
    if avg_min is not None:
        mask_enc = pd.to_numeric(df.get("val_encuestable", pd.Series(1, index=df.index)),
                                 errors="coerce") == 1
        serie_min = pd.to_numeric(df.loc[mask_enc, "val_hours_resolution"],
                                  errors="coerce").dropna() * 60
        p25 = serie_min.quantile(0.25)
        p50 = serie_min.quantile(0.50)
        p75 = serie_min.quantile(0.75)
        p95 = serie_min.quantile(0.95)

        story.append(Paragraph(
            f"La mitjana de temps de resolució és de <b>{_fmt_time(avg_min)}</b> "
            f"(calculat sobre {_fmt(len(serie_min))} consultes encuestables). "
            f"La meitat es resolen en menys de <b>{_fmt_time(p50)}</b> (mediana).",
            S["body"]))
        story.append(Spacer(1, 0.3*cm))

        chart = _chart_temps(df)
        if chart:
            story.append(Image(chart, width=15*cm, height=4.5*cm))
        story.append(Spacer(1, 0.3*cm))

        rows_t = [
            ["Percentil 25",  _fmt_time(p25)],
            ["Mediana (P50)", _fmt_time(p50)],
            ["Mitjana",       _fmt_time(avg_min)],
            ["Percentil 75",  _fmt_time(p75)],
            ["Percentil 95",  _fmt_time(p95)],
        ]
        story.append(_data_table(
            ["Estadístic", "Valor"], rows_t, S,
            col_widths=[9*cm, 8*cm], alignments=["l","r"]
        ))
    else:
        story.append(Paragraph("No hi ha dades de temps disponibles.", S["body"]))

    # ── SECCIÓ 6: Satisfacció i Valoració ────────────────────────────────────
    story += _section_header("6", "Satisfacció i Valoració", S)

    col_enc = "val_media_enc"
    enc_series = pd.to_numeric(df.get(col_enc, pd.Series(dtype=float)), errors="coerce").dropna()
    n_enc = len(enc_series)

    if n_enc > 0:
        enc_mean   = round(enc_series.mean(), 2)
        enc_median = round(enc_series.median(), 2)
        enc_kpis = [
            (f"{enc_mean:.2f}".replace(".", ","),    "Valoració Mitjana",  C_TEAL),
            (f"{enc_median:.2f}".replace(".", ","),  "Valoració Mediana",  C_NAVY),
            (_fmt(n_enc),                            "Enquestes Rebudes",  C_AMBER),
        ]
        # Taxa de resposta
        n_encuestable = int(pd.to_numeric(df.get("val_encuestable", pd.Series(dtype=float)),
                                          errors="coerce").sum()) if "val_encuestable" in df.columns else total
        taxa = round(n_enc / n_encuestable * 100, 1) if n_encuestable else None
        if taxa is not None:
            enc_kpis.append((f"{taxa}%", "Taxa Resposta", C_NAVY))
        story.append(_kpi_cards(enc_kpis, S))
        story.append(Spacer(1, 0.4*cm))

        chart_sat = _chart_satisfaccio(df)
        if chart_sat:
            story.append(Image(chart_sat, width=17*cm, height=5*cm))
        story.append(Spacer(1, 0.4*cm))

        # Taula satisfacció per canal
        if "des_entry_channel" in df.columns:
            sat_canal = (
                df[df[col_enc].notna()]
                .groupby("des_entry_channel")[col_enc]
                .agg(["mean", "count"])
                .rename(columns={"mean": "Mitjana", "count": "Enquestes"})
                .query("Enquestes > 0")
                .sort_values("Enquestes", ascending=False)
            )
            if not sat_canal.empty:
                story.append(Paragraph("Satisfacció per canal d'assistència:", S["body"]))
                story.append(Spacer(1, 0.2*cm))
                rows_sat = [
                    [canal, f"{row['Mitjana']:.2f}".replace(".", ","), _fmt(int(row["Enquestes"]))]
                    for canal, row in sat_canal.iterrows()
                ]
                story.append(_data_table(
                    ["Canal", "Valoració Mitjana", "Enquestes"], rows_sat, S,
                    col_widths=[9*cm, 4.5*cm, 3.5*cm],
                    alignments=["l", "r", "r"]
                ))
    else:
        story.append(Paragraph("No hi ha dades de valoració disponibles per aquest període.", S["body"]))

    doc.build(story, onFirstPage=on_cover, onLaterPages=on_pages)


# ── Funcions principals ───────────────────────────────────────────────────────

def generate_monthly_report(year: int, month: int,
                             endpoint: str = "tickets_enriquits",
                             date_field: str = "td_managed",
                             project: str = "OAC 360º",
                             output_dir: str = "."):
    client = AdtendeClient()
    print("Autenticant...")
    client.login()

    mes = MESOS[month]
    print(f"Descarregant {mes} {year} (filtre: {date_field}, projecte: {project})...")
    df = client.query_month(endpoint, year, month, date_field=date_field, project=project)
    print(f"  {len(df)} registres descarregats.")

    if df.empty:
        print("No hi ha dades per al període seleccionat.")
        return None

    output_path = Path(output_dir) / f"informe_{year}_{month:02d}_{mes}.pdf"
    print("Generant PDF...")
    _build_pdf(df, year, month, f"{mes} {year}", output_path)
    print(f"Informe generat: {output_path}")
    return str(output_path)


def generate_daily_report(year: int, month: int, day: int,
                           endpoint: str = "tickets_enriquits",
                           date_field: str = "td_managed",
                           project: str = "OAC 360º",
                           output_dir: str = "."):
    client = AdtendeClient()
    print("Autenticant...")
    client.login()

    mes = MESOS[month]
    print(f"Descarregant {day:02d} {mes} {year} (filtre: {date_field}, projecte: {project})...")
    df = client.query_date(endpoint, year, month, day, date_field=date_field, project=project)
    print(f"  {len(df)} registres descarregats.")

    if df.empty:
        print("No hi ha dades per al període seleccionat.")
        return None

    output_path = Path(output_dir) / f"informe_{year}_{month:02d}_{day:02d}.pdf"
    print("Generant PDF...")
    _build_pdf(df, year, month, f"{day:02d} {mes} {year}", output_path)
    print(f"Informe generat: {output_path}")
    return str(output_path)


# ── Informe comparatiu ────────────────────────────────────────────────────────

def _metrics(df):
    """Extreu KPIs d'un DataFrame."""
    total = len(df)
    mask_enc = pd.to_numeric(df.get("val_encuestable", pd.Series(1, index=df.index)),
                             errors="coerce") == 1
    avg_min = None
    if "val_hours_resolution" in df.columns:
        t = pd.to_numeric(df.loc[mask_enc, "val_hours_resolution"], errors="coerce").dropna()
        if len(t): avg_min = t.mean() * 60

    avg_rating = None
    if "val_media_enc" in df.columns:
        r = pd.to_numeric(df["val_media_enc"], errors="coerce").dropna()
        if len(r): avg_rating = round(r.mean(), 2)

    flg_res = None
    if "flg_resolution" in df.columns:
        res = pd.to_numeric(df["flg_resolution"], errors="coerce")
        flg_res = round(res.sum() / len(res) * 100, 1) if len(res) else None

    n_enc = int(pd.to_numeric(df["val_media_enc"], errors="coerce").notna().sum()) \
            if "val_media_enc" in df.columns else 0

    cats  = df["des_category_0"].value_counts()   if "des_category_0"   in df.columns else pd.Series()
    canals = df["des_entry_channel"].value_counts() if "des_entry_channel" in df.columns else pd.Series()

    return dict(total=total, avg_min=avg_min, avg_rating=avg_rating,
                flg_res=flg_res, n_enc=n_enc, cats=cats, canals=canals)


def _var_str(v1, v2):
    """Retorna '+X%' o '-X%' de variació."""
    if v1 is None or v2 is None or v1 == 0:
        return "—"
    pct = (v2 - v1) / v1 * 100
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.1f}%".replace(".", ",")


def _chart_evolucion_compare(df1, df2, lbl1, lbl2):
    """Evolució diària: dia del mes a l'eix X, dues línies."""
    _mpl_style()
    fig, ax = plt.subplots(figsize=(13, 3.5))

    for df, color, lbl, ls in [(df1, C_NAVY, lbl1, "-"), (df2, C_TEAL, lbl2, "-")]:
        col = "td_managed" if "td_managed" in df.columns else "td_created"
        s = pd.to_datetime(df[col], errors="coerce").dt.day
        serie = s.value_counts().sort_index()
        ax.plot(serie.index, serie.values, color=color, linewidth=2, linestyle=ls,
                marker="o", markersize=3.5, markerfacecolor="white",
                markeredgecolor=color, markeredgewidth=1.2, label=lbl)
        ax.fill_between(serie.index, serie.values, alpha=0.06, color=color)

    ax.set_xlabel("Dia del mes", fontsize=8)
    ax.set_ylabel("Consultes", fontsize=8)
    ax.legend(fontsize=8, frameon=False)
    ax.set_xticks(range(1, 32))
    ax.tick_params(labelsize=7)
    for sp in ["top", "right"]:
        ax.spines[sp].set_visible(False)
    fig.tight_layout(pad=0.5)
    return _buf(fig)


def _chart_bars_compare(s1, s2, lbl1, lbl2, title="", top_n=10):
    """Barres agrupades per comparar categories o canals."""
    _mpl_style()
    all_keys = list(dict.fromkeys(list(s1.index[:top_n]) + list(s2.index[:top_n])))
    v1 = [s1.get(k, 0) for k in all_keys]
    v2 = [s2.get(k, 0) for k in all_keys]

    y = np.arange(len(all_keys))
    h = 0.35
    fig, ax = plt.subplots(figsize=(13, max(3.5, len(all_keys) * 0.5 + 1)))
    ax.barh(y + h/2, v1, h, color=C_NAVY,  alpha=0.85, label=lbl1)
    ax.barh(y - h/2, v2, h, color=C_TEAL, alpha=0.85, label=lbl2)
    ax.set_yticks(y)
    ax.set_yticklabels(all_keys, fontsize=8)
    ax.set_xlabel("Consultes", fontsize=8)
    if title:
        ax.set_title(title, fontsize=9, fontweight="bold", color=C_NAVY, pad=6)
    ax.legend(fontsize=8, frameon=False)
    for sp in ["top", "right"]:
        ax.spines[sp].set_visible(False)
    ax.tick_params(labelsize=7.5)
    fig.tight_layout(pad=0.6)
    return _buf(fig)


def _build_comparison_pdf(df1, y1, m1, df2, y2, m2, output_path):
    lbl1 = f"{MESOS[m1]} {y1}"
    lbl2 = f"{MESOS[m2]} {y2}"
    periode = f"{lbl1} vs {lbl2}"
    generated = date.today().strftime("%d/%m/%Y")

    S = _S()
    on_cover, on_pages = _callbacks(periode, generated)

    doc = SimpleDocTemplate(
        str(output_path), pagesize=A4,
        leftMargin=1.5*cm, rightMargin=1.5*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm,
        title=f"Informe Comparatiu {periode}", author="Adtende Analytics",
    )

    m1_data = _metrics(df1)
    m2_data = _metrics(df2)
    story = []

    # ── Portada ───────────────────────────────────────────────────────────────
    story.append(Spacer(1, 4.5*cm))
    story.append(Paragraph("Informe Comparatiu<br/>de Consultes", S["cover_title"]))
    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph(periode, S["cover_period"]))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("OAC 360º · Adtende Analytics", S["cover_meta"]))
    story.append(Spacer(1, 3.8*cm))
    story.append(Paragraph(f"Generat el {generated}", S["cover_meta"]))
    story.append(PageBreak())

    # ── Resum de KPIs ─────────────────────────────────────────────────────────
    story += _section_header("1", "Resum Comparatiu de Indicadors", S)

    def _row(label, v1, v2):
        var = _var_str(
            float(str(v1).replace("m","").replace("s","").replace(",",".").split()[0]) if v1 != "—" else None,
            float(str(v2).replace("m","").replace("s","").replace(",",".").split()[0]) if v2 != "—" else None,
        )
        return [label, v1, v2, var]

    total1, total2 = m1_data["total"], m2_data["total"]
    var_total = _var_str(total1, total2)
    kpi_rows = [
        ["Total Consultes",      _fmt(total1),                    _fmt(total2),                    var_total],
        ["Ratio Resolució",
            f"{m1_data['flg_res']}%".replace(".",",") if m1_data['flg_res'] else "—",
            f"{m2_data['flg_res']}%".replace(".",",") if m2_data['flg_res'] else "—",
            _var_str(m1_data['flg_res'], m2_data['flg_res'])],
        ["Temps Resolució",
            _fmt_time(m1_data['avg_min']) if m1_data['avg_min'] else "—",
            _fmt_time(m2_data['avg_min']) if m2_data['avg_min'] else "—",
            _var_str(m1_data['avg_min'], m2_data['avg_min'])],
        ["Valoració Mitjana",
            f"{m1_data['avg_rating']:.2f}".replace(".",",") if m1_data['avg_rating'] else "—",
            f"{m2_data['avg_rating']:.2f}".replace(".",",") if m2_data['avg_rating'] else "—",
            _var_str(m1_data['avg_rating'], m2_data['avg_rating'])],
        ["Enquestes rebudes",    _fmt(m1_data['n_enc']),          _fmt(m2_data['n_enc']),
            _var_str(m1_data['n_enc'], m2_data['n_enc'])],
        ["Categories",           _fmt(len(m1_data['cats'])),      _fmt(len(m2_data['cats'])),      "—"],
        ["Canals actius",        _fmt(len(m1_data['canals'])),    _fmt(len(m2_data['canals'])),     "—"],
    ]

    W = A4[0] - 3*cm
    story.append(_data_table(
        ["Indicador", lbl1, lbl2, "Variació"],
        kpi_rows, S,
        col_widths=[W*0.40, W*0.20, W*0.20, W*0.20],
        alignments=["l", "r", "r", "r"],
    ))

    # ── Secció 2: Evolució diària ─────────────────────────────────────────────
    story.append(Spacer(1, 0.5*cm))
    story += _section_header("2", "Evolució Diària de Consultes", S)
    dies1 = calendar.monthrange(y1, m1)[1]
    dies2 = calendar.monthrange(y2, m2)[1]
    story.append(Paragraph(
        f"<b>{lbl1}</b>: {_fmt(total1)} consultes en {dies1} dies · "
        f"<b>{lbl2}</b>: {_fmt(total2)} consultes en {dies2} dies · "
        f"Variació: <b>{var_total}</b>",
        S["body"]))
    story.append(Spacer(1, 0.3*cm))
    chart = _chart_evolucion_compare(df1, df2, lbl1, lbl2)
    if chart:
        story.append(Image(chart, width=17*cm, height=5*cm))

    # ── Secció 3: Categories ──────────────────────────────────────────────────
    story.append(Spacer(1, 0.4*cm))
    story += _section_header("3", "Distribució per Categoria", S)
    c1, c2 = m1_data["cats"], m2_data["cats"]
    if len(c1) or len(c2):
        chart_cat = _chart_bars_compare(c1, c2, lbl1, lbl2, top_n=12)
        if chart_cat:
            story.append(Image(chart_cat, width=17*cm, height=max(4*cm, min(10*cm, len(set(list(c1.index[:12])+list(c2.index[:12])))*0.55*cm + 1.5*cm))))
        story.append(Spacer(1, 0.3*cm))

        all_cats = dict.fromkeys(list(c1.index[:15]) + list(c2.index[:15]))
        rows_cat = []
        for cat in all_cats:
            v1, v2 = c1.get(cat, 0), c2.get(cat, 0)
            rows_cat.append([cat, _fmt(v1), f"{_pct(v1,total1)}%", _fmt(v2), f"{_pct(v2,total2)}%", _var_str(v1, v2)])
        story.append(_data_table(
            ["Categoria", lbl1, "%", lbl2, "%", "Var."],
            rows_cat, S,
            col_widths=[W*0.34, W*0.13, W*0.10, W*0.13, W*0.10, W*0.20],
            alignments=["l","r","r","r","r","r"],
        ))

    # ── Secció 4: Canals ──────────────────────────────────────────────────────
    story.append(Spacer(1, 0.4*cm))
    story += _section_header("4", "Distribució per Canal", S)
    cn1, cn2 = m1_data["canals"], m2_data["canals"]
    if len(cn1) or len(cn2):
        chart_can = _chart_bars_compare(cn1, cn2, lbl1, lbl2, top_n=10)
        if chart_can:
            story.append(Image(chart_can, width=17*cm, height=max(3.5*cm, min(8*cm, len(set(list(cn1.index)+list(cn2.index)))*0.6*cm + 1.5*cm))))
        story.append(Spacer(1, 0.3*cm))
        all_cans = dict.fromkeys(list(cn1.index) + list(cn2.index))
        rows_can = []
        for can in all_cans:
            v1, v2 = cn1.get(can, 0), cn2.get(can, 0)
            rows_can.append([can, _fmt(v1), f"{_pct(v1,total1)}%", _fmt(v2), f"{_pct(v2,total2)}%", _var_str(v1, v2)])
        story.append(_data_table(
            ["Canal", lbl1, "%", lbl2, "%", "Var."],
            rows_can, S,
            col_widths=[W*0.34, W*0.13, W*0.10, W*0.13, W*0.10, W*0.20],
            alignments=["l","r","r","r","r","r"],
        ))

    # ── Secció 5: Satisfacció ─────────────────────────────────────────────────
    story.append(Spacer(1, 0.4*cm))
    story += _section_header("5", "Satisfacció i Valoració", S)
    sat_kpis = []
    if m1_data["avg_rating"] or m2_data["avg_rating"]:
        r1 = f"{m1_data['avg_rating']:.2f}".replace(".",",") if m1_data["avg_rating"] else "—"
        r2 = f"{m2_data['avg_rating']:.2f}".replace(".",",") if m2_data["avg_rating"] else "—"
        sat_kpis = [
            (r1,          f"Valoració {lbl1}",   C_NAVY),
            (r2,          f"Valoració {lbl2}",   C_TEAL),
            (_fmt(m1_data['n_enc']), f"Enquestes {lbl1}", C_NAVY),
            (_fmt(m2_data['n_enc']), f"Enquestes {lbl2}", C_TEAL),
        ]
        story.append(_kpi_cards(sat_kpis, S))
        story.append(Spacer(1, 0.4*cm))

    # Distribució estreles comparada
    enc1 = pd.to_numeric(df1.get("val_media_enc", pd.Series(dtype=float)), errors="coerce").dropna()
    enc2 = pd.to_numeric(df2.get("val_media_enc", pd.Series(dtype=float)), errors="coerce").dropna()
    if len(enc1) or len(enc2):
        _mpl_style()
        fig, ax = plt.subplots(figsize=(13, 3))
        scores = [5, 4, 3, 2, 1]
        d1 = enc1.value_counts().reindex(scores, fill_value=0)
        d2 = enc2.value_counts().reindex(scores, fill_value=0)
        y = np.arange(len(scores))
        h = 0.35
        ax.barh(y + h/2, d1.values, h, color=C_NAVY, alpha=0.85, label=lbl1)
        ax.barh(y - h/2, d2.values, h, color=C_TEAL, alpha=0.85, label=lbl2)
        ax.set_yticks(y)
        ax.set_yticklabels([f"{'★'*s}" for s in scores], fontsize=9)
        ax.legend(fontsize=8, frameon=False)
        ax.set_xlabel("Enquestes", fontsize=8)
        ax.set_title("Distribució de Valoracions", fontsize=9, fontweight="bold", color=C_NAVY, pad=6)
        for sp in ["top", "right"]:
            ax.spines[sp].set_visible(False)
        fig.tight_layout(pad=0.5)
        story.append(Image(_buf(fig), width=17*cm, height=4*cm))

    doc.build(story, onFirstPage=on_cover, onLaterPages=on_pages)


def generate_comparison_report(year1: int, month1: int, year2: int, month2: int,
                                endpoint: str = "tickets_enriquits",
                                date_field: str = "td_managed",
                                project: str = "OAC 360º",
                                output_dir: str = "."):
    client = AdtendeClient()
    print("Autenticant...")
    client.login()

    lbl1 = f"{MESOS[month1]} {year1}"
    lbl2 = f"{MESOS[month2]} {year2}"

    print(f"Descarregant {lbl1}...")
    df1 = client.query_month(endpoint, year1, month1, date_field=date_field, project=project)
    print(f"  {len(df1)} registres.")

    print(f"Descarregant {lbl2}...")
    df2 = client.query_month(endpoint, year2, month2, date_field=date_field, project=project)
    print(f"  {len(df2)} registres.")

    if df1.empty or df2.empty:
        print("No hi ha dades per a algun dels períodes.")
        return None

    fname = f"comparativa_{year1}_{month1:02d}_vs_{year2}_{month2:02d}.pdf"
    output_path = Path(output_dir) / fname
    print("Generant PDF comparatiu...")
    _build_comparison_pdf(df1, year1, month1, df2, year2, month2, output_path)
    print(f"Informe generat: {output_path}")
    return str(output_path)
