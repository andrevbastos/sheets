"""Cria uma ficha nova (em branco) a partir do template.

Uso: uv run main.py "Nome do Personagem" [caminho/saida.json]
"""
import argparse
import os

from src.sheet_io import create_new_sheet

TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sheets", "sheet-template.json")


def main():
    parser = argparse.ArgumentParser(description="Cria uma ficha nova a partir do template.")
    parser.add_argument("nome", help="nome do personagem")
    parser.add_argument("saida", nargs="?", help="arquivo de saída (padrão: sheets/<nome>.json)")
    args = parser.parse_args()

    output = args.saida or os.path.join("sheets", f"{args.nome}.json")
    if os.path.exists(output):
        parser.error(f"{output} já existe; escolha outro nome para não sobrescrever.")
    create_new_sheet(args.nome, TEMPLATE, output)
    print(f"Ficha criada em {output}")


if __name__ == "__main__":
    main()
