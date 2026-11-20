"""Cria uma ficha nova (em branco) a partir do template.

Uso: uv run main.py "Nome do Personagem" [caminho/saida.json] [--sistema dnd5e|ordem]
"""
import argparse
import os

from src.sheet_io import SYSTEMS, create_new_sheet


def main():
    parser = argparse.ArgumentParser(description="Cria uma ficha nova a partir do template.")
    parser.add_argument("nome", help="nome do personagem")
    parser.add_argument("saida", nargs="?", help="arquivo de saída (padrão: sheets/<nome>.json)")
    parser.add_argument("--sistema", choices=list(SYSTEMS), default="dnd5e",
                        help="dnd5e (padrão) ou ordem (Ordem Paranormal)")
    args = parser.parse_args()

    output = args.saida or os.path.join("sheets", f"{args.nome}.json")
    if os.path.exists(output):
        parser.error(f"{output} já existe; escolha outro nome para não sobrescrever.")
    create_new_sheet(args.nome, args.sistema, output)
    print(f"Ficha criada em {output}")


if __name__ == "__main__":
    main()
