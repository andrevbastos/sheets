"""Lê páginas dos livros em sistemas/ pelo número impresso na página (o que as fichas e o código citam).

Uso (da raiz do projeto):
  uv run --no-project --with pypdf python .claude/skills/criar-ficha/scripts/livro.py ordem 26 27
  uv run --no-project --with pypdf python .claude/skills/criar-ficha/scripts/livro.py jogador 46-48
  uv run --no-project --with pypdf python .claude/skills/criar-ficha/scripts/livro.py ordem --buscar "Escolhido pelo Outro Lado"

Livros: ordem (livro básico de Ordem Paranormal), jogador (Livro do Jogador de D&D 5e, PT-BR),
tasha (Caldeirão de Tasha, PT-BR; sem número impresso, então a página é a do PDF).
O Guia do Mestre (regras-mestre.pdf) é fotografado e não tem texto, por isso não está aqui.
"""
import json
import logging
import os
import sys
import tempfile

logging.disable(logging.WARNING)  # o pypdf reclama de fontes, sem afetar o texto

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
# livro -> (arquivo, quanto somar ao número impresso para achar a página do PDF)
LIVROS = {
    "ordem": ("sistemas/ordem-paranormal/ordem-paranormal.pdf", 10),
    "jogador": ("sistemas/dnd-5e/regras-jogador.pdf", 1),
    "tasha": ("sistemas/dnd-5e/Tasha_s Cauldron PT-BR.pdf", 0),
}


CACHE = os.path.join(tempfile.gettempdir(), "criar-ficha-livros")


def textos(livro, caminho):
    """Texto de todas as páginas do PDF. A primeira leitura demora; depois vem do cache."""
    os.makedirs(CACHE, exist_ok=True)
    cache = os.path.join(CACHE, f"{livro}-{int(os.path.getmtime(caminho))}.json")
    if os.path.exists(cache):
        with open(cache, encoding="utf-8") as f:
            return json.load(f)
    from pypdf import PdfReader
    lidos = [p.extract_text() or "" for p in PdfReader(caminho).pages]
    with open(cache, "w", encoding="utf-8") as f:
        json.dump(lidos, f, ensure_ascii=False)
    return lidos


def paginas(args):
    for arg in args:
        if "-" in arg:
            ini, fim = arg.split("-", 1)
            yield from range(int(ini), int(fim) + 1)
        else:
            yield int(arg)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 3 or sys.argv[1] not in LIVROS:
        print(__doc__)
        sys.exit(1)
    arquivo, desvio = LIVROS[sys.argv[1]]
    caminho = os.path.join(RAIZ, arquivo)
    if not os.path.exists(caminho):
        sys.exit(f"Livro não encontrado: {arquivo} (os PDFs ficam fora do git; peça ao usuário para colocá-lo lá)")
    lidos = textos(sys.argv[1], caminho)

    if sys.argv[2] == "--buscar":
        termos = [t.lower() for t in sys.argv[3:]]
        for i, texto in enumerate(lidos):
            texto = texto.lower()
            if all(t in texto for t in termos):
                linha = next((l.strip() for l in texto.splitlines() if termos[0] in l), "")
                print(f"p. {i + 1 - desvio}: {linha[:120]}")
        return

    for numero in paginas(sys.argv[2:]):
        indice = numero + desvio - 1
        if not 0 <= indice < len(lidos):
            print(f"\n===== p. {numero}: fora do livro")
            continue
        print(f"\n===== p. {numero}\n{lidos[indice] or '(sem texto)'}")


if __name__ == "__main__":
    main()
