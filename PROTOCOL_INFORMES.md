# Protocol de creació d'informes de client — INFORMES AUTOMÁTICOS

## Estructura de la taula

Dos columnes de valors per cada període:
- **Ràtio Ajuntament**: dades del municipi concret
- **Ràtio General**: mitjana de tots els municipis en el mateix rang de dates

---

## Lògica de colors (Ràtio Ajuntament vs Ràtio General)

### 🟢 VERD = millor que la mitjana (per sobre és bo)
- % Població atesa
- Grau de satisfacció /5 (i subpreguntes 2.1, 2.2, 2.3)
- Utilització del TRUCA'M
- Assistències franja horària de tarda
- Consultes sobre Campanyes puntuals

### 🔴 VERMELL = pitjor que la mitjana (per sobre és dolent)
- **Temps mig consulta** → menys temps = millor servei
- **Assistències Catàleg de tràmits** → moltes consultes = la gent no sap fer tràmits sola
- **Assistències Cita prèvia** → moltes cites = més càrrega presencial
- **Trucades per centraleta** → moltes derivacions = menys autonomia del ciutadà

### ⚫ NEGRE = sense diferència significativa o no comparable

---

## Nomenclatura de municipis a l'API

Els municipis apareixen en **MAJÚSCULES** a l'API (`des_client`).
Exemples: `OLOT`, `CALDES DE MONTBUI`, `ROSES`, `CARDEDEU`, `ESPARREGUERA`

---

## Indicadors calculats

| # | Indicador | Camp API |
|---|---|---|
| — | Total assistències | count(tickets) |
| 1 | % Població atesa | total / val_population × 100 |
| 2 | Grau satisfacció /5 | val_rating (val_encuestable==1) |
| 2.1 | Qualitat del servei | val_pregunta1 |
| 2.2 | Resolució consulta | val_pregunta2 |
| 2.3 | Tracte de l'agent | val_pregunta3 |
| 3 | Temps mig consulta | val_time_spent (minuts) |
| 4 | Ús TRUCA'M | des_entry_channel IN ['TRUCA'M LOCUCIO','TRUCA'M WEB'] |
| 5 | Franja tarda | flg_morning_schedule == '15-24h' |
| 6 | Cita prèvia | des_category_0 == 'Cita Prèvia' |
| 7 | Catàleg de tràmits | des_category_1 IN ['Catàleg de tràmits','eTramitador'] |
| 8 | Campanyes puntuals | des_category_1 IN [llista campanyes] |
| 10 | Trucades centraleta | des_category_1 == 'Trucada per centraleta' |

---

## Filtre de dades

- **Endpoint**: `tickets_enriquits` (UUID: 70c7001b-ba8a-413c-b5e8-4724e6d803bb)
- **Projecte**: `OAC 360º`
- **Filtre doble**: `td_managed` i `td_created` dins del rang de dates

---

## Format de sortida

1. **Taula web** → localhost HTML (grisa, neta, sense floritures)
2. **Excel** → full `Indicadors` (colors verd/vermell) + full `Dades raw`
