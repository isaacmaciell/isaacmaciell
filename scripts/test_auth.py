"""Testa a autenticação no Artia usando as variáveis de ambiente ARTIA_*.

Uso: python scripts/test_auth.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from artia_mcp.client import ArtiaClient, ArtiaConfig, ArtiaError  # noqa: E402


def main() -> int:
    try:
        client = ArtiaClient(ArtiaConfig.from_env())
        token = client.authenticate(force=True)
    except ArtiaError as exc:
        print(f"FALHA: {exc}")
        return 1
    print(f"OK: autenticado no Artia (token com {len(token)} caracteres).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
