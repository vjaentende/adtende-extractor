# INFORMES AUTOMÀTICS — Adtende Analytics

Sistema Python per generar informes mensuals automàtics des de l'API de Adtende/Intelek.

## Estructura del projecte

- `api_client.py` — Client API (login, query, query_month, query_date)
- `config.py` — Credencials (.env) i UUIDs dels endpoints
- `report_generator.py` — Generació d'informes Word (.docx) amb python-docx
- `sacar_datos.py` — Informe de Client (taula KPI per municipi, Excel + HTML localhost)
- `main.py` — CLI amb argparse
- `requirements.txt` — dependencies

## Com generar informes

### Informe de Servei (5 Word, un per servei)
```python
from report_generator import generate_all_monthly_reports
generate_all_monthly_reports(2026, 3)  # març 2026
```
Genera 5 fitxers: OAC360, OAC360_Social, OAC360_Tributs, SATEDIBA, Centraleta.

### Informe de Client (taula KPI per municipi)
```python
from sacar_datos import main
# o executar: python sacar_datos.py --municipio OLOT --from 2025-01-01 --to 2026-05-15
```

---

## ⚠️ REGLES CRÍTIQUES — obligatòries sempre

### 1. FILTRE DOBLE OBLIGATORI (td_managed + td_created)
El BI aplica **sempre dos filtres de data simultàniament**: `td_managed` I `td_created` han d'estar AMBDÓS dins del rang. Si es filtra només per un, el recompte no coincideix amb el BI.

```python
# CORRECTE:
df = full[
    (full['td_managed'] >= 'YYYY-MM-DD') & (full['td_managed'] < 'YYYY-MM-DD') &
    (full['td_created'] >= 'YYYY-MM-DD') & (full['td_created'] < 'YYYY-MM-DD')
]
# INCORRECTE: filtrar només per td_managed o només per td_created
```

Implementat a `report_generator._apply_dual_date_filter()`.

### 2. COMPARACIÓ DE DATES: strings, NO datetime
`pd.to_datetime(..., errors='coerce')` genera NaT en registres amb dates no parseables (dades 2021-2022), excloent ~900 registres silenciosament.

```python
# CORRECTE: comparar com strings YYYY-MM-DD
(full['td_managed'] >= '2021-10-06') & (full['td_managed'] < '2022-10-07')

# INCORRECTE:
full['td_managed_dt'] = pd.to_datetime(full['td_managed'], errors='coerce')
```

### 3. val_time_spent està en MINUTS (no en segons)
La documentació diu "bigint — Temps imputat total (en segons)" però els valors reals són **minuts**.

### 4. La API falla amb rangs anuals complets
No fer una sola query per a un any complet. Descarregar **mes a mes** i concatenar.

### 5. Filtre de projecte: client-side, no via API
Sempre filtrar per `des_project` client-side després de descarregar. Enviar-ho com a filtre API dona 400.

### 6. Satisfacció: val_encuestable==1 NO garanteix val_rating no nul
Filtrar sempre: `df[(df['val_encuestable']==1) & (df['val_rating'].notna())]`

### 7. Límit de data: usar < dia+1, mai <= dia
`<= '2022-10-06'` com a string exclou tickets d'aquell dia amb timestamp posterior a les 00:00. Usar sempre `< '2022-10-07'`.

---

## Endpoints disponibles (tots a tickets_enriquits)

L'únic endpoint que funciona de forma fiable és `tickets_enriquits`. Els altres endpoints de config.py donen 500.

Filtrar per `des_project`:
| Servei | des_project |
|--------|-------------|
| OAC 360 | `OAC 360º` |
| OAC 360 Social | `OAC 360º SOCIAL` |
| OAC 360 Tributs | `OAC 360º Tributs` |
| SATE DIBA | `SATE DIBA` |
| Centraleta | `Centraleta` |

Municipis sempre en MAJÚSCULES: `OLOT`, `CALDES DE MONTBUI`, `ROSES`, `CARDEDEU`, etc.

---

## Lògica de colors — Informe de Client

### Indicadors on MÉS BAIX = MILLOR (vermell si per sobre de la mitjana)
- Temps mig consulta
- Assistències Catàleg tràmits
- Assistències Cita prèvia
- Trucades per centraleta

### Indicadors on MÉS ALT = MILLOR (verd si per sobre de la mitjana)
- % Població atesa
- Grau de satisfacció /5 (i subpreguntes 2.1, 2.2, 2.3)
- Utilització del TRUCA'M
- Assistències franja tarda
- Campanyes puntuals

---

## Idioma
**Tots els informes s'han de redactar en català.**

## Format de sortida
- Informe de Servei → **Word (.docx)**
- Informe de Client → **Excel (.xlsx)** + **HTML (localhost:8765)**

---

## Configuració local (.env)
```
ADTENDE_USERNAME=el_teu_usuari
ADTENDE_PASSWORD=la_teva_contrasenya
```
