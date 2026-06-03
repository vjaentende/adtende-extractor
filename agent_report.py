"""
Informe d'agent — Adtende Analytics + Bizneo HCM
=================================================
Genera l'informe individual d'un agent comparant:
  - Trucades reals (API Adtende, endpoint tickets_enriquits)
  - Mínim exigible calculat a partir de la jornada real (Bizneo API)

Fórmula (extreta del full "MINIM EXIGIBLE" de l'Excel RRHH):
    mínim_mensual = 54.4 × (hores_contracte/39) × dies_treballats_mes
    On: 54.4 = (34h_actives/5_dies) × 8_trucades/hora_activa

Ús:
    python agent_report.py --agent PV --mes 2026-05 --trucades 423
    python agent_report.py --agent SG --mes 2026-04 --trucades 312

Agents disponibles:
    SG  → Susanna   (Operador 1)
    SB  → Sergio    (Operador 2)
    SGV → Sandra    (Operador 4)
    DC  → David     (Operador 5)
    GH  → Guillem   (Operador 6)
    AM  → Arnau     (Operador 7)
    AS  → Aitana    (Operador 8)
    PV  → Pau       (Agent 1)
    LMK → Laura     (Agent 2)
    BC  → Belén     (Agent 3)
"""

import argparse
import calendar
from datetime import date, timedelta
from functools import lru_cache

# ─── Configuració Bizneo ──────────────────────────────────────────────────────

BIZNEO_BASE  = "https://adtende.bizneohr.com/api/v1"
BIZNEO_TOKEN = "SFMyNTY.g2gDdAAAAAJ3AmlkbQAAACQwZGIyZDM5Ni0yZDg2LTQzNWMtOGMwYi1kMGMwNDZmZTBhYmR3CmNvbXBhbnlfaWRiAO2q5G4GAM4t3oeeAWIAAVGA.bB27l1ee8EVFEe8jTLCGYWDQsraP2L81ANlwlRqn0wQ"

# ─── Configuració agents ──────────────────────────────────────────────────────
#
# hores_setmana: hores de contracte setmanals (39h estàndard, 25h ANA JAÉN)
# bizneo_id:     ID de l'usuari a Bizneo HCM (None si no s'ha trobat)

AGENTS = {
    "SG":  {"nom": "Susanna",  "rol": "Operador 1", "hores_setmana": 39, "bizneo_id": None},
    "SB":  {"nom": "Sergio",   "rol": "Operador 2", "hores_setmana": 39, "bizneo_id": 15800447},
    "SGV": {"nom": "Sandra",   "rol": "Operador 4", "hores_setmana": 39, "bizneo_id": 15800443},
    "DC":  {"nom": "David",    "rol": "Operador 5", "hores_setmana": 39, "bizneo_id": None},
    "GH":  {"nom": "Guillem",  "rol": "Operador 6", "hores_setmana": 39, "bizneo_id": None},
    "AM":  {"nom": "Arnau",    "rol": "Operador 7", "hores_setmana": 39, "bizneo_id": None},
    "AS":  {"nom": "Aitana",   "rol": "Operador 8", "hores_setmana": 39, "bizneo_id": 15800441},
    "PV":  {"nom": "Pau",      "rol": "Agent 1",    "hores_setmana": 39, "bizneo_id": 15800448},
    "LMK": {"nom": "Laura",    "rol": "Agent 2",    "hores_setmana": 39, "bizneo_id": 15800449},
    "BC":  {"nom": "Belén",    "rol": "Agent 3",    "hores_setmana": 39, "bizneo_id": None},
}

# ─── Paràmetres del mínim exigible (font: MINIM EXIGIBLE sheet) ───────────────

MINIM_TRUCADES_HORA          = 8      # trucades/hora activa — KPI central
HORES_SETMANA_ESTANDARD      = 39.0   # jornada complerta referència
DESCANS_HORES_DIA            = 1.0    # 1h descans per dia (jornades > 30h/setmana)
HORES_ACTIVES_SETMANA_STD    = 34.0   # 39h - 5 dies × 1h = 34h actives
# trucades/dia jornada complerta = (34h/5dies) × 8 trucades/hora = 54.4
TRUCADES_DIA_JORNADA_COMPLERTA = (HORES_ACTIVES_SETMANA_STD / 5) * MINIM_TRUCADES_HORA


def dies_laborables_mes(any_: int, mes: int) -> list[date]:
    """Retorna tots els dies laborables (Dl–Dv) d'un mes."""
    _, num_dies = calendar.monthrange(any_, mes)
    return [
        date(any_, mes, d)
        for d in range(1, num_dies + 1)
        if date(any_, mes, d).weekday() < 5
    ]


def calcular_minim(hores_setmana: float, dies_treballats: int) -> dict:
    """
    Calcula el mínim exigible per a un agent donades les seves hores de
    contracte i els dies efectivament treballats al mes.

    Fórmula exacta de l'Excel (full MINIM EXIGIBLE, cel·la C30/D30):
        trucades_dia  = 54.4 × (hores_setmana / 39)
        minim_mensual = trucades_dia × dies_treballats
    """
    trucades_dia = TRUCADES_DIA_JORNADA_COMPLERTA * (hores_setmana / HORES_SETMANA_ESTANDARD)
    minim        = trucades_dia * dies_treballats

    # Referència jornada complerta (20 dies, 39h)
    dies_ref  = 20
    minim_ref = TRUCADES_DIA_JORNADA_COMPLERTA * dies_ref  # 1.088

    return {
        "hores_setmana":    hores_setmana,
        "dies_treballats":  dies_treballats,
        "trucades_dia":     round(trucades_dia, 1),
        "minim_exigible":   round(minim),
        "minim_ref_complet": round(minim_ref),
        "pct_jornada":      round(dies_treballats / dies_ref * 100, 1),
    }


# ─── Client Bizneo HCM ────────────────────────────────────────────────────────
#
# Comportament observat de l'API (juny 2026):
#  - GET /absences retorna 100 registres únics (la paginació diu 1221 però repeteix)
#  - Els filtres user_id/start_date/end_date s'ignoren → filtre client-side
#  - GET /users retorna 20 usuaris actius accessibles amb aquest token

class BizneoClie:
    """Client Bizneo HCM. Cacheja les absències per evitar crides repetides."""

    def __init__(self, token: str = BIZNEO_TOKEN, base: str = BIZNEO_BASE):
        import requests
        self.token   = token
        self.base    = base
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        self._absencies_cache: list[dict] | None = None

    def _get(self, endpoint: str, params: dict = None) -> dict:
        params = {**(params or {}), "token": self.token}
        r = self.session.get(f"{self.base}{endpoint}", params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    def _totes_absencies(self) -> list[dict]:
        """Descarrega totes les absències (deduplicades per id)."""
        if self._absencies_cache is not None:
            return self._absencies_cache
        seen, result = set(), []
        page = 1
        while True:
            data = self._get("/absences", {"page_size": 100, "page_number": page})
            nous = [a for a in data["absences"] if a["id"] not in seen]
            for a in nous:
                seen.add(a["id"])
                result.append(a)
            # L'API repeteix dades a partir de la pàgina 2; sortim si no hi ha nous
            if not nous or page >= data["pagination"]["total_pages"]:
                break
            page += 1
        self._absencies_cache = result
        return result

    def dies_absencia_mes(self, user_id: int, any_: int, mes: int,
                           estats: tuple = ("approved",)) -> list[date]:
        """
        Retorna els dies laborables d'absència d'un usuari en un mes concret.
        Inclou absències que solapen parcialment el mes.
        """
        mes_inici = date(any_, mes, 1)
        _, nd = calendar.monthrange(any_, mes)
        mes_fi = date(any_, mes, nd)

        dies: set[date] = set()
        for a in self._totes_absencies():
            if a["user_id"] != user_id:
                continue
            if a["state"] not in estats:
                continue
            d_start = max(date.fromisoformat(a["start_at"]), mes_inici)
            d_end   = min(date.fromisoformat(a["end_at"]),   mes_fi)
            if d_start > d_end:
                continue
            curr = d_start
            while curr <= d_end:
                if curr.weekday() < 5:
                    dies.add(curr)
                curr += timedelta(days=1)
        return sorted(dies)


# ─── Generació de l'informe ───────────────────────────────────────────────────

def generar_informe_agent(
    codi_agent: str,
    any_: int,
    mes: int,
    trucades_reals: int,
    dies_absencia: list[date] = None,
    bizneo: BizneoClie = None,
) -> dict:
    """
    Genera l'informe complet d'un agent per a un mes.

    Si es passa `bizneo`, obté les absències automàticament de Bizneo.
    Si es passa `dies_absencia`, usa aquells dies directament.
    Si cap dels dos, assumeix assistència complerta.
    """
    agent = AGENTS.get(codi_agent)
    if not agent:
        raise ValueError(f"Agent desconegut: {codi_agent}. Opcions: {list(AGENTS)}")

    # Obtenir dies d'absència
    if dies_absencia is None:
        dies_absencia = []
        if bizneo and agent["bizneo_id"]:
            dies_absencia = bizneo.dies_absencia_mes(agent["bizneo_id"], any_, mes)

    dies_absencia_set = set(dies_absencia)
    tots_dies_lab     = dies_laborables_mes(any_, mes)
    dies_treballats   = [d for d in tots_dies_lab if d not in dies_absencia_set]

    minim = calcular_minim(agent["hores_setmana"], len(dies_treballats))

    diferencia = trucades_reals - minim["minim_exigible"]
    compliment = trucades_reals >= minim["minim_exigible"]

    return {
        "agent":             codi_agent,
        "nom":               agent["nom"],
        "mes":               f"{any_}-{mes:02d}",
        "hores_setmana":     minim["hores_setmana"],
        "dies_laborables":   len(tots_dies_lab),
        "dies_absencia":     len(dies_absencia_set),
        "dies_treballats":   minim["dies_treballats"],
        "trucades_dia":      minim["trucades_dia"],
        "minim_exigible":    minim["minim_exigible"],
        "minim_ref_complet": minim["minim_ref_complet"],
        "pct_jornada":       minim["pct_jornada"],
        "trucades_reals":    trucades_reals,
        "diferencia":        diferencia,
        "compliment":        compliment,
        "bizneo_actiu":      bizneo is not None and agent["bizneo_id"] is not None,
        "dies_absencia_list": dies_absencia,
    }


def imprimir_informe(inf: dict):
    sep   = "─" * 54
    estat = "COMPLERT" if inf["compliment"] else "NO COMPLERT"
    flag  = "✅" if inf["compliment"] else "❌"
    biz   = "Bizneo" if inf["bizneo_actiu"] else "Manual/sense dades"

    print(f"\n{sep}")
    print(f"  INFORME AGENT — {inf['nom']} ({inf['agent']}) — {inf['mes']}")
    print(f"{sep}")
    print(f"  Hores contracte/setmana  : {inf['hores_setmana']}h")
    print(f"  Dies laborables del mes  : {inf['dies_laborables']}")
    print(f"  Dies absència            : {inf['dies_absencia']}  [{biz}]")
    print(f"  Dies treballats efectius : {inf['dies_treballats']}")
    print(f"  % jornada complerta      : {inf['pct_jornada']}%")
    print(f"{sep}")
    print(f"  Trucades mínimes/dia     : {inf['trucades_dia']}")
    print(f"  Mínim exigible mes       : {inf['minim_exigible']} trucades")
    print(f"  Referència jornada 100%  : {inf['minim_ref_complet']} trucades")
    print(f"{sep}")
    print(f"  Trucades reals           : {inf['trucades_reals']} trucades")
    print(f"  Diferència               : {inf['diferencia']:+d} trucades")
    print(f"  Estat                    : {flag} {estat}")
    print(f"{sep}\n")

    if inf["dies_absencia_list"]:
        print(f"  Dies d'absència ({len(inf['dies_absencia_list'])}):")
        for d in inf["dies_absencia_list"]:
            print(f"    · {d.strftime('%d/%m/%Y (%A)')}")
        print()


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Informe agent Adtende")
    parser.add_argument("--agent",    required=True, help="Codi agent (ex: PV, SG, AM)")
    parser.add_argument("--mes",      required=True, help="Mes (ex: 2026-05)")
    parser.add_argument("--trucades", type=int, default=0,
                        help="Trucades reals ateses")
    parser.add_argument("--no-bizneo", action="store_true",
                        help="No consultar Bizneo (absències = 0)")
    args = parser.parse_args()

    any_m, mes_m = map(int, args.mes.split("-"))

    biz = None if args.no_bizneo else BizneoClie()

    inf = generar_informe_agent(args.agent, any_m, mes_m, args.trucades, bizneo=biz)
    imprimir_informe(inf)
