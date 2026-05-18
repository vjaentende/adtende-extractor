#!/usr/bin/env python3
"""
Generador de informes — Adtende Analytics
Uso:
    python main.py                              # mes anterior
    python main.py --year 2026 --month 2        # febrer 2026
    python main.py --date 2026-04-16            # dia concret
    python main.py --endpoint tickets_oac360_social
    python main.py --list-endpoints
"""

import argparse
import sys
from datetime import date

from config import ENDPOINTS
from report_generator import generate_monthly_report, generate_daily_report, generate_comparison_report


def previous_month():
    today = date.today()
    if today.month == 1:
        return today.year - 1, 12
    return today.year, today.month - 1


def main():
    parser = argparse.ArgumentParser(description="Generador d'informes Adtende Analytics")
    parser.add_argument("--year",  type=int, help="Any de l'informe")
    parser.add_argument("--month", type=int, help="Mes de l'informe (1-12)")
    parser.add_argument("--date",  type=str, help="Dia concret (format YYYY-MM-DD)")
    parser.add_argument(
        "--endpoint", default="tickets_oac360", choices=list(ENDPOINTS.keys()),
        help="Endpoint a usar (default: tickets_oac360)",
    )
    parser.add_argument("--output-dir", default=".", help="Directori de sortida")
    parser.add_argument("--list-endpoints", action="store_true", help="Llista endpoints i surt")
    parser.add_argument("--compare", nargs=2, metavar=("YYYY-MM", "YYYY-MM"),
                        help="Genera informe comparatiu entre dos mesos (ex: 2025-01 2026-01)")
    args = parser.parse_args()

    if args.list_endpoints:
        print("\nEndpoints disponibles:")
        for name, uuid in ENDPOINTS.items():
            tag = "(solo interno)" if name == "tickets_enriquits" else "(compartible)"
            print(f"  {name:35s} {tag}  [{uuid}]")
        sys.exit(0)

    print(f"\n=== Informe Adtende Analytics ===")

    # Mode comparatiu
    if args.compare:
        try:
            y1, m1 = [int(x) for x in args.compare[0].split("-")]
            y2, m2 = [int(x) for x in args.compare[1].split("-")]
        except ValueError:
            parser.error("Format incorrecte per --compare. Usa YYYY-MM (ex: 2025-01 2026-01)")
        generate_comparison_report(y1, m1, y2, m2, output_dir=args.output_dir)
        print("Fet.")
        return

    # Mode dia concret
    if args.date:
        try:
            d = date.fromisoformat(args.date)
        except ValueError:
            parser.error("Format de data incorrecte. Usa YYYY-MM-DD (ex: 2026-04-16)")
        generate_daily_report(d.year, d.month, d.day, output_dir=args.output_dir)

    # Mode mensual
    else:
        if args.year and args.month:
            year, month = args.year, args.month
        elif args.year or args.month:
            parser.error("Indica --year i --month junts, o cap dels dos.")
        else:
            year, month = previous_month()

        if not (1 <= month <= 12):
            parser.error("El mes ha d'estar entre 1 i 12.")

        generate_monthly_report(year, month, output_dir=args.output_dir)

    print("Fet.")


if __name__ == "__main__":
    main()
