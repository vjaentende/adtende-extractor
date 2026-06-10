#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI — Servidor d'informes Adtende
Escolta al port 8080. n8n (Docker) el crida via host.docker.internal:8080
"""
import os
import shutil
from datetime import date
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from report_generator import generate_all_monthly_reports, generate_quarterly_report

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR   = Path.home() / "Desktop" / "INFORMES_2026"
SCRIPT_DIR = Path(__file__).parent
TODAY      = date.today().strftime("%d%m%Y")

SERVEI_MAP = {
    "OAC360_Social":  "OAC360 SOCIAL",
    "OAC360_Tributs": "TRIBUTS",
    "OAC360":         "OAC360",
    "SATEDIBA":       "SATEDIBA",
    "Centraleta":     "CENTRALETA",
}

MESOS_CAT = {
    1:"Gener", 2:"Febrer", 3:"Març", 4:"Abril",
    5:"Maig",  6:"Juny",   7:"Juliol", 8:"Agost",
    9:"Setembre", 10:"Octubre", 11:"Novembre", 12:"Desembre",
}

app = FastAPI(title="Adtende Informes API", version="1.0")


def _carpeta_mes(year: int, month: int) -> Path:
    mes = MESOS_CAT[month]
    p = BASE_DIR / f"{month:02d}_{mes}"
    p.mkdir(parents=True, exist_ok=True)
    return p

def _carpeta_q(year: int, quarter: int) -> Path:
    mesos_q = {1:[1,2,3], 2:[4,5,6], 3:[7,8,9], 4:[10,11,12]}
    ms = mesos_q[quarter]
    noms = "_".join(MESOS_CAT[m] for m in ms)
    p = BASE_DIR / f"Q{quarter}_Trimestral_{noms}"
    p.mkdir(parents=True, exist_ok=True)
    return p

def _rename_and_move(src: Path, dest_dir: Path) -> Path:
    """Renombra a INF SERVEI DDMMYYYY.docx i mou a dest_dir."""
    nom = src.stem
    servei_key = None
    for k in SERVEI_MAP:
        if nom.endswith(k):
            servei_key = k
            break
    label = SERVEI_MAP.get(servei_key, nom)
    nou_nom = f"INF {label} {TODAY}.docx"
    dst = dest_dir / nou_nom
    shutil.move(str(src), str(dst))
    return dst


# ── Models ────────────────────────────────────────────────────────────────────
class MensualRequest(BaseModel):
    year: int
    month: int  # 1-12

class TrimestralRequest(BaseModel):
    year: int
    quarter: int  # 1-4


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/")
def health():
    return {"status": "ok", "versio": "1.0"}


@app.post("/mensual")
def generar_mensual(req: MensualRequest):
    """Genera els 5 informes mensuals i els desa a INFORMES_2026/MM_Mes/"""
    if not (1 <= req.month <= 12):
        raise HTTPException(400, "month ha de ser entre 1 i 12")

    tmp_dir = SCRIPT_DIR
    try:
        paths = generate_all_monthly_reports(req.year, req.month, output_dir=str(tmp_dir))
    except Exception as e:
        raise HTTPException(500, f"Error generant informes: {e}")

    dest = _carpeta_mes(req.year, req.month)
    finals = []
    for p in paths:
        src = Path(p)
        if src.exists():
            dst = _rename_and_move(src, dest)
            finals.append(str(dst))

    return {
        "ok": True,
        "mes": MESOS_CAT[req.month],
        "any": req.year,
        "fitxers": finals,
        "carpeta": str(dest),
    }


@app.post("/trimestral")
def generar_trimestral(req: TrimestralRequest):
    """Genera els 5 informes trimestrals comparatius."""
    if not (1 <= req.quarter <= 4):
        raise HTTPException(400, "quarter ha de ser entre 1 i 4")

    tmp_dir = SCRIPT_DIR
    try:
        paths = generate_quarterly_report(req.year, req.quarter, output_dir=str(tmp_dir))
    except Exception as e:
        raise HTTPException(500, f"Error generant trimestral: {e}")

    dest = _carpeta_q(req.year, req.quarter)
    finals = []
    for p in paths:
        src = Path(p)
        if src.exists():
            dst = _rename_and_move(src, dest)
            finals.append(str(dst))

    return {
        "ok": True,
        "trimestre": f"Q{req.quarter}",
        "any": req.year,
        "fitxers": finals,
        "carpeta": str(dest),
    }


@app.get("/download")
def download(path: str):
    """Descarrega un fitxer .docx pel seu path absolut."""
    f = Path(path)
    if not f.exists() or f.suffix != ".docx":
        raise HTTPException(404, "Fitxer no trobat")
    return FileResponse(str(f), media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", filename=f.name)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_informes:app", host="0.0.0.0", port=8080, reload=False)
