"""Sincroniza o Artia com uma planilha Gantt (xlsx ou csv no formato de exportação).

Por padrão só SIMULA e mostra o plano. Para gravar, use --apply.
Exclusões exigem --allow-delete além de --apply.

Uso:
  python scripts/sync_gantt.py planilha.xlsx [--sheet "Gantt Comparativo"]
  python scripts/sync_gantt.py planilha.xlsx --apply [--fallback-responsible 307979] [--allow-delete]
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import logging  # noqa: E402

from artia_mcp import server, sync  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--sheet")
    ap.add_argument("--apply", action="store_true", help="grava no Artia (padrão: só simula)")
    ap.add_argument("--allow-delete", action="store_true", help="permite excluir atividades (com --apply)")
    ap.add_argument("--fallback-responsible", type=int, help="userId usado quando o responsável da planilha não existe no Artia")
    args = ap.parse_args()

    logging.getLogger("httpx").setLevel(logging.WARNING)
    rows = sync.load_sheet(args.file, args.sheet)
    folder_ids = {int(r.id[1:]) for r in rows if r.kind == "folder"}
    state = sync.fetch_state(server, folder_ids)
    plan = sync.build_plan(rows, state, args.fallback_responsible)
    print(sync.format_plan(plan))
    if not args.apply:
        print("\n(simulação: nada foi gravado; use --apply para aplicar)")
        return 0
    print("\nAplicando...")
    for line in sync.apply_plan(server, state, plan, allow_delete=args.allow_delete):
        print(" -", line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
