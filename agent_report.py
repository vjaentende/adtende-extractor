"""
Informe d'agent — Adtende Analytics + Bizneo HCM
=================================================
Genera l'informe individual d'un agent comparant:
  - Trucades reals (API Adtende, endpoint tickets_enriquits)
  - Mínim exigible calculat a partir de la jornada real (Bizneo API)

Ús:
    python agent_report.py --agent PV --mes 2026-05
    python agent_report.py --agent SG --mes 2026-04

Agents disponibles:
    SG  → Susanna   (Operador 1)
    SB  → Sergio    (Operador 2)
    SGV → Sandra    (Operador 4)
    DC  → David     (Operador 5)
    GH  → Guillem   (Operador 5/6)
    AM  → Arnau     (Operador 7)
    AS  → Aitana    (Operador 8)
    PV  → Pau       (Agent 1)
    LMK → Laura     (Agent 2)
    BC  → Belén     (Agent 3)
"""

import argparse
from datetime import date, timedelta
import calendar
import pandas as pd

# ─── Configuració agents ──────────────────────────────────────────────────────

AGENTS = {
    "SG":  {"nom": "Susanna",  "rol": "Operador 1", "bizneo_id": None},
    "SB":  {"nom": "Sergio",   "rol": "Operador 2", "bizneo_id": None},
    "SGV": {"nom": "Sandra",   "rol": "Operador 4", "bizneo_id": None},
    "DC":  {"nom": "David",    "rol": "Operador 5", "bizneo_id": None},
    "GH":  {"nom": "Guillem",  "rol": "Operador 6", "bizneo_id": None},
    "AM":  {"nom": "Arnau",    "rol": "Operador 7", "bizneo_id": None},
    "AS":  {"nom": "Aitana",   "rol": "Operador 8", "bizneo_id": None},
    "PV":  {"nom": "Pau",      "rol": "Agent 1",    "bizneo_id": None},
    "LMK": {"nom": "Laura",    "rol": "Agent 2",    "bizneo_id": None},
    "BC":  {"nom": "Belén",    "rol": "Agent 3",    "bizneo_id": None},
}

# ─── Lògica de mínim exigible (extreta del full "MINIM EXIGIBLE") ─────────────
#
# Font: ESTADIS CALCUL MIN EXIGIBLES RRHH 23042026.xlsx → full "MINIM EXIGIBLE"
#
# Paràmetres base:
#   - Durada mitja trucada          : 4.5 min (3.6 cita prèvia / 6.5 tràmits)
#   - Jornada setmanal complerta    : 39 h
#   - Descans per dia treballat     : 1 h (5 h/setmana)
#   - Hores actives setmana complerta: 34 h (39 - 5)
#   - Hores actives mes complert    : 136 h (34 × 4 setmanes)
#   - Mínim exigible/hora activa    : 8 trucades
#   - Mínim exigible jornada complerta/mes: 1.088 trucades (136 × 8)
#
# Fórmula per a qualsevol agent:
#   mínim_mensual = hores_actives_reals × 8
#
#   On: hores_actives_reals = hores_treballades - (dies_treballats × 1h_descans)
#
# Proporcionalitat:
#   Si l'agent treballa menys hores (parcial, absències, vacances),
#   el mínim baixa exactament proporcional a les hores actives.

MINIM_TRUCADES_PER_HORA_ACTIVA = 8       # trucades/hora activa (mínim exigible)
DESCANS_PER_DIA_HORES          = 1.0    # 1h descans per cada dia treballat
HORES_JORNADA_COMPLERTA        = 39.0   # hores/setmana jornada complerta
SETMANES_MES                   = 4.0    # setmanes/mes (aprox.)


def calcular_hores_actives(hores_treballades: float, dies_treballats: int) -> float:
    """
    Retorna les hores actives (sense descansos) d'un agent.
    hores_treballades: total hores de jornada del mes
    dies_treballats:   dies laborables efectivament treballats (sense absències)
    """
    descans_total = dies_treballats * DESCANS_PER_DIA_HORES
    return max(0.0, hores_treballades - descans_total)


def calcular_minim_exigible(hores_actives: float) -> float:
    """
    Mínim de trucades exigible per a un agent amb les hores actives donades.
    """
    return hores_actives * MINIM_TRUCADES_PER_HORA_ACTIVA


def calcular_minim_proporcional(hores_treballades: float, dies_treballats: int) -> dict:
    """
    Retorna un dict amb tots els valors del mínim exigible per a un agent.
    """
    hores_actives = calcular_hores_actives(hores_treballades, dies_treballats)
    minim         = calcular_minim_exigible(hores_actives)

    # Referència jornada complerta
    dies_ref       = int(SETMANES_MES * 5)           # 20 dies laborables
    hores_ref      = HORES_JORNADA_COMPLERTA * SETMANES_MES  # 156h brutes
    hores_act_ref  = calcular_hores_actives(hores_ref, dies_ref)  # 136h
    minim_ref      = calcular_minim_exigible(hores_act_ref)       # 1088

    return {
        "hores_jornada":    hores_treballades,
        "dies_treballats":  dies_treballats,
        "hores_actives":    round(hores_actives, 2),
        "minim_exigible":   round(minim),
        "minim_ref_complet": round(minim_ref),
        "pct_jornada":      round(hores_actives / hores_act_ref * 100, 1) if hores_act_ref > 0 else 0,
    }


# ─── Horaris per setmana (extrets del full "HORARI SETMANA X") ───────────────
#
# Cada agent té hores per dia per cada tipus de setmana.
# Clau: (codi_agent, num_setmana) → {dia: hores}
# Setmanes: 1, 2, 3, 4 (dins del mes)
# Dies: L=Dilluns, M=Dimarts, X=Dimecres, J=Dijous, V=Divendres
#
# Font: fulls "HORARI SETMANA 1", "HORARI SETMANA 2 I 4", "HORARI SETMANA 3"
#       i fulls individuals per agent (SG, SB, SGV, DC, GH, AM, AS, PV, LMK, BC)

HORARI_AGENTS = {
    # SG - Susanna — jornada 39h/setmana, horari fix
    ("SG", 1): {"L": 7, "M": 7, "X": 7, "J": 7, "V": 7},
    ("SG", 2): {"L": 7, "M": 7, "X": 7, "J": 7, "V": 7},
    ("SG", 3): {"L": 7, "M": 7, "X": 7, "J": 7, "V": 7},
    ("SG", 4): {"L": 7, "M": 7, "X": 7, "J": 7, "V": 7},

    # SB - Sergio — horari rotatiu, setmana 4 diferent
    ("SB", 1): {"L": 7,  "M": 7,  "X": 10, "J": 7,  "V": 7},
    ("SB", 2): {"L": 7,  "M": 7,  "X": 10, "J": 7,  "V": 7},
    ("SB", 3): {"L": 7,  "M": 7,  "X": 10, "J": 7,  "V": 7},
    ("SB", 4): {"L": 7,  "M": 7,  "X": 7,  "J": 7,  "V": 10},  # setmana 4 diferent

    # SGV - Sandra
    ("SGV", 1): {"L": 10, "M": 7,  "X": 10, "J": 6,  "V": 10},
    ("SGV", 2): {"L": 10, "M": 7,  "X": 10, "J": 6,  "V": 10},
    ("SGV", 3): {"L": 10, "M": 7,  "X": 10, "J": 6,  "V": 6},
    ("SGV", 4): {"L": 10, "M": 7,  "X": 10, "J": 6,  "V": 6},

    # DC - David — jornada parcial 26h
    ("DC", 1): {"L": 10, "M": 9,  "X": 10, "J": 0,  "V": 0},
    ("DC", 2): {"L": 10, "M": 9,  "X": 10, "J": 0,  "V": 0},
    ("DC", 3): {"L": 10, "M": 10, "X": 9,  "J": 0,  "V": 0},
    ("DC", 4): {"L": 10, "M": 10, "X": 9,  "J": 0,  "V": 0},

    # GH - Guillem
    ("GH", 1): {"L": 10, "M": 10, "X": 6,  "J": 8,  "V": 5},
    ("GH", 2): {"L": 10, "M": 10, "X": 6,  "J": 8,  "V": 5},
    ("GH", 3): {"L": 10, "M": 10, "X": 6,  "J": 8,  "V": 5},
    ("GH", 4): {"L": 10, "M": 10, "X": 6,  "J": 8,  "V": 5},

    # AM - Arnau — setmanes 1/3 vs 2/4
    ("AM", 1): {"L": 7,  "M": 7,  "X": 7,  "J": 7,  "V": 7},
    ("AM", 2): {"L": 7,  "M": 9,  "X": 7,  "J": 10, "V": 6},
    ("AM", 3): {"L": 7,  "M": 6,  "X": 6,  "J": 10, "V": 10},
    ("AM", 4): {"L": 7,  "M": 9,  "X": 7,  "J": 10, "V": 6},

    # AS - Aitana
    ("AS", 1): {"L": 7,  "M": 9,  "X": 9,  "J": 7,  "V": 7},
    ("AS", 2): {"L": 7,  "M": 9,  "X": 9,  "J": 7,  "V": 7},
    ("AS", 3): {"L": 7,  "M": 9,  "X": 9,  "J": 7,  "V": 7},
    ("AS", 4): {"L": 7,  "M": 9,  "X": 9,  "J": 7,  "V": 7},

    # PV - Pau — setmanes 1/3/4 vs 2
    ("PV", 1): {"L": 7,  "M": 8,  "X": 9,  "J": 7,  "V": 8},
    ("PV", 2): {"L": 7,  "M": 8,  "X": 7,  "J": 7,  "V": 10},
    ("PV", 3): {"L": 7,  "M": 8,  "X": 9,  "J": 7,  "V": 8},
    ("PV", 4): {"L": 7,  "M": 8,  "X": 9,  "J": 7,  "V": 8},

    # LMK - Laura
    ("LMK", 1): {"L": 9,  "M": 7,  "X": 7,  "J": 9,  "V": 7},
    ("LMK", 2): {"L": 9,  "M": 7,  "X": 7,  "J": 9,  "V": 7},
    ("LMK", 3): {"L": 9,  "M": 7,  "X": 7,  "J": 9,  "V": 7},
    ("LMK", 4): {"L": 9,  "M": 7,  "X": 7,  "J": 9,  "V": 7},

    # BC - Belén
    ("BC", 1): {"L": 7,  "M": 10, "X": 7,  "J": 8,  "V": 7},
    ("BC", 2): {"L": 7,  "M": 10, "X": 7,  "J": 8,  "V": 7},
    ("BC", 3): {"L": 7,  "M": 10, "X": 7,  "J": 8,  "V": 7},
    ("BC", 4): {"L": 7,  "M": 10, "X": 7,  "J": 8,  "V": 7},
}

DIA_NUM = {0: "L", 1: "M", 2: "X", 3: "J", 4: "V"}  # weekday() → codi dia


def num_setmana_del_mes(d: date) -> int:
    """Retorna el número de setmana dins del mes (1-4) per a una data donada."""
    primer_dia = d.replace(day=1)
    # Quina setmana del mes és (1-indexed)
    return ((d.day - 1) // 7) + 1


def hores_mes_per_horari(codi_agent: str, any: int, mes: int,
                          dies_absencia: list[date] = None) -> dict:
    """
    Calcula les hores i dies treballats per a un agent en un mes concret,
    descomptant els dies d'absència si es proporcionen.

    Retorna: {"hores": float, "dies": int, "detall": [...]}
    """
    dies_absencia = dies_absencia or []
    any_mes = date(any, mes, 1)
    _, num_dies = calendar.monthrange(any, mes)

    hores_total = 0.0
    dies_total  = 0
    detall      = []

    for dia_num in range(1, num_dies + 1):
        d = date(any, mes, dia_num)
        if d.weekday() >= 5:   # cap de setmana
            continue
        if d in dies_absencia:
            detall.append({"data": d, "hores": 0, "absencia": True})
            continue

        num_s  = num_setmana_del_mes(d)
        num_s  = min(num_s, 4)          # màxim 4
        codi_d = DIA_NUM[d.weekday()]
        horari = HORARI_AGENTS.get((codi_agent, num_s), {})
        hores  = horari.get(codi_d, 0)

        hores_total += hores
        if hores > 0:
            dies_total += 1
        detall.append({"data": d, "hores": hores, "absencia": False})

    return {"hores": hores_total, "dies": dies_total, "detall": detall}


# ─── Client Bizneo (pendent de token) ────────────────────────────────────────

class BizneoClie:
    """
    Client per a la API Bizneo HCM.
    Base URL: https://connect.bizneo.com/hcm/v1/
    Auth: token per query param (?token=XXX)
    """
    BASE = "https://connect.bizneo.com/hcm/v1"

    def __init__(self, token: str):
        import requests
        self.token   = token
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def _get(self, endpoint: str, params: dict = None):
        params = params or {}
        params["token"] = self.token
        r = self.session.get(f"{self.BASE}/{endpoint}", params=params)
        r.raise_for_status()
        return r.json()

    def empleats(self, pagina: int = 1, per_pagina: int = 100):
        """Llista d'empleats actius."""
        return self._get("users", {"page": pagina, "per_page": per_pagina})

    def absencies_mes(self, user_id: int, any: int, mes: int):
        """Absències d'un empleat en un mes concret."""
        d_from = date(any, mes, 1).isoformat()
        _, nd  = calendar.monthrange(any, mes)
        d_to   = date(any, mes, nd).isoformat()
        return self._get(f"users/{user_id}/absences",
                         {"start_date": d_from, "end_date": d_to})


# ─── Generació de l'informe ───────────────────────────────────────────────────

def generar_informe_agent(codi_agent: str, any: int, mes: int,
                           trucades_reals: int,
                           dies_absencia: list[date] = None,
                           bizneo_token: str = None) -> dict:
    """
    Genera l'informe complet d'un agent per a un mes.

    Args:
        codi_agent:     Codi de l'agent (ex: 'PV')
        any, mes:       Mes a analitzar
        trucades_reals: Trucades ateses (de l'API Adtende)
        dies_absencia:  Llista de dates d'absència (opcional, es pot obtenir de Bizneo)
        bizneo_token:   Token Bizneo per obtenir absències automàticament

    Returns: dict amb tots els KPIs de l'informe
    """
    agent = AGENTS.get(codi_agent)
    if not agent:
        raise ValueError(f"Agent desconegut: {codi_agent}. Opcions: {list(AGENTS)}")

    # Obtenir absències de Bizneo si hi ha token
    if bizneo_token and agent["bizneo_id"]:
        client = BizneoClie(bizneo_token)
        raw    = client.absencies_mes(agent["bizneo_id"], any, mes)
        # TODO: parsejar raw per extreure dies concrets d'absència
        # dies_absencia = _parsejar_absencies(raw)

    # Hores i dies treballats
    jornada = hores_mes_per_horari(codi_agent, any, mes, dies_absencia)

    # Mínim exigible
    minim   = calcular_minim_proporcional(jornada["hores"], jornada["dies"])

    # Comparació
    diferencia = trucades_reals - minim["minim_exigible"]
    compliment = trucades_reals >= minim["minim_exigible"]

    return {
        "agent":            codi_agent,
        "nom":              agent["nom"],
        "mes":              f"{any}-{mes:02d}",
        "hores_jornada":    minim["hores_jornada"],
        "dies_treballats":  minim["dies_treballats"],
        "hores_actives":    minim["hores_actives"],
        "pct_jornada":      minim["pct_jornada"],
        "minim_exigible":   minim["minim_exigible"],
        "trucades_reals":   trucades_reals,
        "diferencia":       diferencia,
        "compliment":       compliment,
    }


def imprimir_informe(inf: dict):
    sep = "─" * 52
    estat = "✅ COMPLERT" if inf["compliment"] else "❌ NO COMPLERT"
    print(f"\n{sep}")
    print(f"  INFORME AGENT — {inf['nom']} ({inf['agent']}) — {inf['mes']}")
    print(f"{sep}")
    print(f"  Hores jornada mes      : {inf['hores_jornada']}h")
    print(f"  Dies treballats        : {inf['dies_treballats']}")
    print(f"  Hores actives (sense descans): {inf['hores_actives']}h")
    print(f"  % sobre jornada complerta    : {inf['pct_jornada']}%")
    print(f"{sep}")
    print(f"  Mínim exigible         : {inf['minim_exigible']} trucades")
    print(f"  Trucades reals         : {inf['trucades_reals']} trucades")
    print(f"  Diferència             : {inf['diferencia']:+d} trucades")
    print(f"  Estat                  : {estat}")
    print(f"{sep}\n")


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Informe agent Adtende")
    parser.add_argument("--agent",    required=True, help="Codi agent (ex: PV, SG, AM)")
    parser.add_argument("--mes",      required=True, help="Mes (ex: 2026-05)")
    parser.add_argument("--trucades", type=int,      help="Trucades reals (si no es passa s'obtenen de l'API)")
    args = parser.parse_args()

    any_m, mes_m = map(int, args.mes.split("-"))

    # TODO: si no es passen trucades, obtenir-les automàticament de l'API Adtende
    trucades = args.trucades or 0

    inf = generar_informe_agent(args.agent, any_m, mes_m, trucades)
    imprimir_informe(inf)
