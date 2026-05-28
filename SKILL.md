---
name: informe-executiu-bi
description: >
  Genera informes ejecutivos formales a partir de datos de BI (Adtende/Intelek).
  Usa esta skill SIEMPRE que se pida generar, completar o revisar un informe de cliente
  o de servicio con datos del BI: tablas de indicadores, análisis de tendencias,
  comparativas entre municipios, heatmaps de uso, distribución por canales o agentes.
  También se activa cuando se detectan anomalías, caídas de servicio o patrones
  relevantes en los datos que deban comunicarse a dirección o cliente.
---

# Skill: Generador de Informes Ejecutivos BI

## Propósito

Producir informes formales, sobrios y ejecutivos a partir de datos del BI de Adtende.
El informe debe ser útil para dirección o cliente sin necesidad de explicaciones adicionales.

---

## Reglas de análisis

### 1. Detección automática de hallazgos

Antes de redactar, analiza SIEMPRE estos patrones:

- **Caída de servicio**: total de atenciones < 80% de la media del período anterior o general.
- **Degradación de SLA**: tiempo medio de consulta > 20% por encima de la media general.
- **Satisfacción crítica**: val_rating medio < 3,5 o caída > 0,3 puntos respecto período anterior.
- **Pico o caída anómala**: variación mensual o semanal > ±25% sin causa conocida.
- **Concentración horaria**: si > 40% de las atenciones se concentran en una franja, indicarlo.
- **Concentración por canal**: si un canal supera el 70% del total, indicarlo.
- **Incidencias recurrentes**: categorías que aparecen en los top 3 en ≥ 3 períodos consecutivos.
- **Patrón operativo**: franja tarda con crecimiento sostenido ≥ 2 períodos consecutivos.

### 2. Lógica de colores en indicadores (protocolo fijo)

| Indicador | Verde (mejor) | Rojo (peor) |
|---|---|---|
| % Población atendida | Por encima de media | Por debajo |
| Satisfacción /5 | Por encima | Por debajo |
| Tiempo medio consulta | Por debajo (más rápido) | Por encima |
| Catálogo de trámites | Por debajo (más autonomía) | Por encima |
| Cita previa | Por debajo (menos carga) | Por encima |
| Llamadas centralita | Por debajo (más autonomía) | Por encima |
| TRUCA'M | Por encima | Por debajo |
| Franja tarde | Por encima | Por debajo |
| Campañas puntuales | Por encima | Por debajo |

### 3. Conclusiones: reglas estrictas

- Cada conclusión debe estar respaldada por un dato concreto del dataset.
- Ordenar por impacto: primero lo crítico, luego lo relevante, luego lo informativo.
- Formato: **[Hallazgo]** → dato que lo soporta → implicación operativa (si aplica).
- Prohibido: "es importante destacar", "cabe señalar", "se observa una tendencia positiva".
- Si falta contexto para interpretar un dato, escribir literalmente: *"Sin contexto suficiente para interpretar este dato."*
- No inventar causas. Solo describir lo que muestran los datos.

---

## Reglas de visualización

### Cuándo usar cada visual

| Visual | Usar cuando |
|---|---|
| **Tabla** | Detalle exacto de indicadores, comparativas con valores precisos, más de 4 categorías |
| **Mapa de calor** | Intensidad por hora×día, distribución temporal de volumen de atenciones |
| **Barras** | Comparativa entre categorías, municipios, canales o agentes |
| **Líneas** | Evolución temporal (diaria, semanal, mensual) |
| **Tarta/donut** | Solo para composiciones simples con ≤ 5 segmentos y diferencias visibles |

**Prohibido:** gráficos decorativos, gráficos 3D, dobles ejes sin justificación, gráficos que no aporten información que no esté ya en la tabla.

### Replicar la lógica visual del BI

- Las tablas del informe deben mantener los mismos indicadores, en el mismo orden, que el BI original.
- Los números deben coincidir con los del BI (usar filtro doble td_managed + td_created).
- Si un indicador aparece en el BI pero no en los datos disponibles, indicarlo explícitamente.
- Las franjas horarias se definen igual que en el BI: "08-15h" y "15-24h".
- Los canales se nombran igual que en el BI: TELEFON, TRUCA'M LOCUCIO, TRUCA'M WEB, PRESENCIAL.

---

## Guía visual del documento

### Tipografía
- **Títulos de sección**: Arial o sistema, 14px/pt, negrita, mayúsculas o versalitas.
- **Subtítulos**: 12px/pt, negrita, sin mayúsculas.
- **Cuerpo de texto**: 11px/pt, regular, interlineado 1.4.
- **Valores en tabla**: 11px/pt, negrita, alineados a la derecha.
- **Notas al pie / aclaraciones**: 9px/pt, gris #777, cursiva.

### Colores
- Teal `#00A89D` → valor mejor que la media.
- Rojo `#D9534F` → valor peor que la media.
- Negro `#222` → valores sin diferencia significativa o datos generales.
- Gris `#777` → texto secundario, notas, contexto.
- Fondo blanco. Sin colores de fondo en filas salvo alternado sutil (#f9f9f9).

### Estructura y espaciado
- Separar secciones con línea divisoria o espacio equivalente a 1.5× la altura de línea.
- No usar más de 2 niveles de jerarquía visual por sección.
- Las tablas no deben superar 6 columnas. Si hay más, dividir en dos tablas.
- Densidad: máximo 15 filas por tabla sin paginación o separación visual.

### Densidad visual
- Un gráfico por hallazgo principal. No acumular visualizaciones.
- Si el dato se entiende solo con la tabla, no añadir gráfico.
- El informe debe poder leerse en 3 minutos. Si no, está sobrecargado.

---

## Estructura del informe

```
1. Encabezado
   - Municipio / cliente
   - Período analizado
   - Fecha de generación

2. Resumen ejecutivo (máx. 5 líneas)
   - Total atenciones
   - Hallazgo principal positivo
   - Hallazgo principal negativo o de atención
   - Comparativa respecto media general (1 dato)

3. Tabla de indicadores
   - Ràtio Ajuntament | Ràtio General
   - Colores según protocolo

4. Hallazgos y análisis (solo si hay datos suficientes)
   - Ordenados por impacto
   - Cada uno con dato de soporte

5. Visualizaciones (solo las necesarias)
   - Mapa de calor si hay datos horarios
   - Evolución si hay ≥ 3 períodos

6. Conclusiones operativas
   - Máx. 4 puntos
   - Formato: hallazgo → dato → implicación

7. Nota de datos (si procede)
   - Meses sin datos por API 502
   - Indicadores sin suficientes encuestas
```
