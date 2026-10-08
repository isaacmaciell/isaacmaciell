"""Baixa o schema da API do Artia via introspecção e salva em schema/.

Gera schema/artia_schema.json (introspecção bruta) e schema/artia_schema.graphql
(SDL legível), e imprime as queries e mutations disponíveis.

Uso: python scripts/dump_schema.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from graphql import build_client_schema, print_schema  # noqa: E402

from artia_mcp.client import ArtiaClient, ArtiaConfig, ArtiaError  # noqa: E402


def main() -> int:
    try:
        data = ArtiaClient(ArtiaConfig.from_env()).introspect()
    except ArtiaError as exc:
        print(f"FALHA: {exc}")
        return 1

    out = ROOT / "schema"
    out.mkdir(exist_ok=True)
    (out / "artia_schema.json").write_text(json.dumps(data, indent=2, ensure_ascii=False))
    schema = build_client_schema(data)
    (out / "artia_schema.graphql").write_text(print_schema(schema))

    for label, root in (("Queries", schema.query_type), ("Mutations", schema.mutation_type)):
        if root is None:
            continue
        print(f"\n{label} ({len(root.fields)}):")
        for name, fld in sorted(root.fields.items()):
            args = ", ".join(f"{a}: {arg.type}" for a, arg in fld.args.items())
            print(f"  {name}({args}): {fld.type}")
    print(f"\nSchema salvo em {out}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
