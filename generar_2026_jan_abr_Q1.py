#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera els informes mensuals de Gener i Abril 2026 (falten)
+ l'informe trimestral comparatiu Q1 2026 (Gen, Feb, Mar).

Executa: python3 -u generar_2026_jan_abr_Q1.py
"""
import sys
sys.stdout.reconfigure(line_buffering=True)

from report_generator import generate_all_monthly_reports, generate_quarterly_report

OUTPUT_DIR = "/Users/victorjaenruiz/Desktop/INFORMES_AUTOMATICOS_API"
YEAR = 2026

print("=" * 60)
print("  GENERACIÓ INFORMES 2026 — Gener, Abril + Q1 Trimestral")
print("=" * 60)

# ── 1. Gener 2026 ─────────────────────────────────────────────
print("\n\n▶▶▶  GENER 2026  ◀◀◀")
generate_all_monthly_reports(YEAR, 1, output_dir=OUTPUT_DIR)

# ── 2. Abril 2026 ─────────────────────────────────────────────
print("\n\n▶▶▶  ABRIL 2026  ◀◀◀")
generate_all_monthly_reports(YEAR, 4, output_dir=OUTPUT_DIR)

# ── 3. Q1 Trimestral (Gen, Feb, Mar 2026) ─────────────────────
print("\n\n▶▶▶  TRIMESTRAL Q1 2026 (Gener · Febrer · Març)  ◀◀◀")
generate_quarterly_report(YEAR, 1, output_dir=OUTPUT_DIR)

print("\n\n" + "=" * 60)
print("  TOT COMPLETAT ✅")
print("=" * 60)
