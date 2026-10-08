"""Valida as operações de artia_mcp/operations.py contra o schema baixado.

Rode depois de scripts/dump_schema.py. Aponta operações, argumentos ou campos
que não existem no schema real, para ajuste em operations.py.

Uso: python scripts/validate_operations.py [caminho/artia_schema.json]
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from graphql import build_client_schema, parse, validate  # noqa: E402

from artia_mcp import operations as ops  # noqa: E402


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "schema" / "artia_schema.json"
    if not path.exists():
        print(f"Schema não encontrado em {path}. Rode scripts/dump_schema.py antes.")
        return 1
    schema = build_client_schema(json.loads(path.read_text()))

    docs = {"AUTHENTICATE": ops.AUTHENTICATE}
    docs.update({name: spec.document(spec.arg_types) for name, spec in ops.ALL_OPERATIONS.items()})

    failures = 0
    for name, document in docs.items():
        errors = validate(schema, parse(document))
        if errors:
            failures += 1
            print(f"[ERRO] {name}")
            for err in errors:
                print(f"    - {err.message}")
        else:
            print(f"[OK]   {name}")
    print(f"\n{len(docs) - failures}/{len(docs)} operações válidas.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
