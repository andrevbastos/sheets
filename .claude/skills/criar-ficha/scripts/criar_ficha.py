"""Monta uma ficha a partir das escolhas, confere as regras de criação dos livros e salva em sheets/.

Uso (da raiz do projeto):
  uv run python .claude/skills/criar-ficha/scripts/criar_ficha.py escolhas.json            # confere e salva
  uv run python .claude/skills/criar-ficha/scripts/criar_ficha.py escolhas.json --conferir # só confere
  ... --saida sheets/outra.json   ... --sobrescrever

`escolhas.json` é uma ficha parcial no formato do app (veja references/ordem.md e references/dnd.md).
Os valores derivados (PV/PE/SAN, modificadores, bônus, Defesa, CD...) não precisam vir: o app calcula.
As perícias podem vir pela chave ("investigacao") ou pelo nome ("Investigação").

Saída: um resumo com os números calculados e a lista de AVISOS (o que foge da regra de criação).
Aviso não impede salvar: o mestre pode ter liberado uma exceção. Sai com código 2 se houver avisos.
"""
import argparse
import json
import math
import os
import re
import sys
import unicodedata

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, RAIZ)

from src import dnd, ordem, sheet_io  # noqa: E402


def plain(text) -> str:
    text = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", text).strip().lower()


def nome_arquivo(nome: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", plain(nome)).strip("-") or "personagem"


def chaves_pericias(pericias, tabela):
    """Aceita a perícia pela chave ou pelo nome do livro."""
    if not isinstance(pericias, dict):
        return pericias
    por_nome = {plain(nome): key for key, nome, *_ in tabela}
    por_nome.update({plain("Enganação"): "blefar"} if tabela is dnd.PERICIAS else {})
    saida = {}
    for k, v in pericias.items():
        key = k if k in {t[0] for t in tabela} else por_nome.get(plain(k), k)
        saida[key] = v
    return saida


# ------------------------------------------------------------------ Ordem Paranormal
# Perícias treinadas da classe além das da origem (p. 25, 29, 33): fixas + escolhidas (+ Intelecto)
ORDEM_PERICIAS_CLASSE = {"combatente": 1 + 2, "especialista": 7, "ocultista": 2 + 3}
# Grau de Treinamento em NEX 35% e 70%: quantas perícias sobem, antes de somar o Intelecto
ORDEM_GRAU = {"combatente": 2, "especialista": 5, "ocultista": 3}
ORDEM_HABILIDADE_5 = {"combatente": ["Ataque Especial"], "especialista": ["Eclético", "Perito"],
                      "ocultista": ["Escolhido pelo Outro Lado"]}
ORDEM_PROGRESSAO = {  # Tabelas 1.3, 1.4 e 1.5 (p. 25, 29 e 33)
    "combatente": {5: "Ataque Especial (2 PE, +5)", 25: "Ataque Especial (3 PE, +10)",
                   55: "Ataque Especial (4 PE, +15)", 85: "Ataque Especial (5 PE, +20)"},
    "especialista": {5: "Eclético, Perito (2 PE, +1d6)", 25: "Perito (3 PE, +1d8)",
                     40: "Engenhosidade (veterano)", 55: "Perito (4 PE, +1d10)",
                     75: "Engenhosidade (expert)", 85: "Perito (5 PE, +1d12)"},
    "ocultista": {5: "Escolhido pelo Outro Lado (1º círculo)", 25: "Escolhido pelo Outro Lado (2º círculo)",
                  55: "Escolhido pelo Outro Lado (3º círculo)", 85: "Escolhido pelo Outro Lado (4º círculo)"},
}
ORDEM_COMUM = {10: "habilidade de trilha", 15: "poder de classe", 20: "aumento de atributo",
               30: "poder de classe", 35: "grau de treinamento", 40: "habilidade de trilha",
               45: "poder de classe", 50: "aumento de atributo e versatilidade", 60: "poder de classe",
               65: "habilidade de trilha", 70: "grau de treinamento", 75: "poder de classe",
               80: "aumento de atributo", 90: "poder de classe", 95: "aumento de atributo",
               99: "habilidade de trilha"}
CIRCULO_POR_NEX = [(85, 4), (55, 3), (25, 2), (5, 1)]


def conferir_ordem(s, avisos):
    cls, nex = ordem.class_key(s), s["nex"]
    attrs = s["atributos"]
    if cls is None:
        avisos.append(f"Classe '{s['classe']}' não é do livro (Combatente, Especialista ou Ocultista, p. 22).")
    if ordem.origin_key(s) is None:
        avisos.append(f"Origem '{s['origem']}' não é uma das 26 do livro (Tabela 1.1, p. 19).")

    aumentos = sum(1 for n in (20, 50, 80, 95) if n <= nex)
    soma, esperado = sum(attrs.values()), 9 + aumentos
    if soma != esperado:
        avisos.append(f"Atributos somam {soma}; o esperado é {esperado} (todos em 1 + 4 pontos, p. 13"
                      + (f", + {aumentos} aumento(s) de atributo pelo NEX" if aumentos else "") + ").")
    zeros = [k for k, v in attrs.items() if v == 0]
    if len(zeros) > 1:
        avisos.append(f"Só um atributo pode ser reduzido a 0 (p. 13); estão em 0: {', '.join(zeros)}.")
    teto = 3 if aumentos == 0 else 5
    altos = [f"{k.upper()} {v}" for k, v in attrs.items() if v > teto]
    if altos:
        avisos.append(f"Atributo acima de {teto} ({'inicial máximo 3, p. 13' if teto == 3 else 'máximo 5'}): "
                      + ", ".join(altos) + ".")
    if aumentos and max(attrs.values()) > 3 + aumentos:
        avisos.append("Algum atributo passou de 3 mais que o número de aumentos de atributo do NEX permite.")

    if cls:
        per = s["pericias"]
        treinadas = [k for k, p in per.items() if p["treino"] >= 5]
        esperado = 2 + ORDEM_PERICIAS_CLASSE[cls] + attrs["int"]
        if len(treinadas) != esperado:
            avisos.append(f"{len(treinadas)} perícias treinadas; o esperado é {esperado} (2 da origem + "
                          f"{ORDEM_PERICIAS_CLASSE[cls]} da classe + INT {attrs['int']}, p. 22 e 39). "
                          "Poderes como Treinamento em Perícia somam mais.")
        if cls == "combatente":
            if not {"luta", "pontaria"} & set(treinadas):
                avisos.append("Combatente precisa ser treinado em Luta ou Pontaria (p. 25).")
            if not {"fortitude", "reflexos"} & set(treinadas):
                avisos.append("Combatente precisa ser treinado em Fortitude ou Reflexos (p. 25).")
        if cls == "ocultista" and not {"ocultismo", "vontade"} <= set(treinadas):
            avisos.append("Ocultista é treinado em Ocultismo e Vontade (p. 33).")
        veteranos = [k for k, p in per.items() if p["treino"] >= 10]
        experts = [k for k, p in per.items() if p["treino"] >= 15]
        graus = sum(1 for n in (35, 70) if n <= nex)
        limite = graus * (ORDEM_GRAU[cls] + attrs["int"])
        if len(veteranos) + len(experts) > limite:
            avisos.append(f"{len(veteranos)} perícias veteranas ou expert; o Grau de Treinamento do NEX "
                          f"{nex}% dá {limite} aumento(s) de grau (NEX 35% e 70%).")
        if experts and nex < 70:
            avisos.append("Expert só a partir do segundo Grau de Treinamento (NEX 70%).")

        nomes = {ordem._sem_genero(h["nome"]) for h in s["habilidades"]}  # "Escolhida" vale
        faltam = [h for h in ORDEM_HABILIDADE_5[cls] if ordem._sem_genero(h) not in nomes]
        if faltam:
            avisos.append(f"Faltam as habilidades de NEX 5% da classe em 'habilidades': {', '.join(faltam)}.")
        if nex >= 10 and not s.get("trilha"):
            avisos.append("NEX 10% ou mais: escolha a trilha (p. 24, 28, 32).")

        if cls == "ocultista":
            esperados = 3 + ordem.nex_nivel(s) - 1
            if len(s["rituais"]) < esperados:
                avisos.append(f"{len(s['rituais'])} ritual(is); o ocultista começa com 3 de 1º círculo e aprende "
                              f"mais um por NEX (esperado {esperados} no NEX {nex}%, p. 32).")
            circulo = next(c for n, c in CIRCULO_POR_NEX if nex >= n)
            altos = [r["nome"] for r in s["rituais"] if r["circulo"] > circulo]
            if altos:
                avisos.append(f"Rituais acima do {circulo}º círculo no NEX {nex}%: {', '.join(altos)}.")
    if s.get("trilha") and nex < 10:
        avisos.append("Trilha só a partir de NEX 10%.")
    if s.get("afinidade") and nex < ordem.NEX_AFINIDADE:
        avisos.append("Afinidade só a partir de NEX 50% (p. 114).")

    inv = s["inventario"]
    contagem = ordem.itens_por_categoria(s)
    for cat, n in contagem.items():
        if n > inv["limite_itens"][cat]:
            avisos.append(f"{n} itens de categoria {cat}; a patente {inv['patente']} permite "
                          f"{inv['limite_itens'][cat]} (Tabela 3.1, p. 52).")
    if ordem.espacos_usados(s) > inv["carga_max"]:
        avisos.append(f"Itens ocupam {ordem.espacos_usados(s)} espaços; a carga máxima é {inv['carga_max']} "
                      "(sobrecarregado: −5 em Defesa e perícias de carga, p. 63).")


def resumo_ordem(s):
    cls = ordem.class_key(s)
    attrs = "  ".join(f"{sig} {s['atributos'][k]}" for k, sig, _ in ordem.ATRIBUTOS)
    treinadas = [f"{nome}{'' if s['pericias'][k]['treino'] == 5 else ' (' + dict(ordem.GRAUS)[s['pericias'][k]['treino']].lower() + ')'}"
                 for k, nome, *_ in ordem.PERICIAS if s["pericias"][k]["treino"] >= 5]
    linhas = [
        f"{s['nome']} — {s['classe'] or '?'} NEX {s['nex']}%, origem {s['origem'] or '?'}"
        + (f", trilha {ordem.TRILHA[s['trilha']][1]}" if s.get("trilha") else ""),
        f"Atributos: {attrs}",
        f"PV {s['pv']['max']}  PE {s['pe']['max']} ({s['pe_rodada']}/rodada)  SAN {s['san']['max']}  "
        f"Defesa {ordem.defesa_total(s)}  DT rituais {s['dt_rituais']}  Carga {ordem.espacos_usados(s)}/"
        f"{s['inventario']['carga_max']}",
        f"Treinadas ({len(treinadas)}): {', '.join(treinadas)}",
    ]
    if s["habilidades"]:
        linhas.append("Habilidades: " + ", ".join(h["nome"] for h in s["habilidades"]))
    if s["rituais"]:
        linhas.append("Rituais: " + ", ".join(f"{r['nome']} ({r['circulo']}º)" for r in s["rituais"]))
    if s["ataques"]:
        linhas.append("Ataques: " + ", ".join(f"{a['nome']} {a['teste']} {a['dano']}" for a in s["ataques"]))
    if cls:
        marcos = {**ORDEM_COMUM, **ORDEM_PROGRESSAO[cls]}
        ganhos = [f"{n}% {marcos[n]}" for n in sorted(marcos) if n <= s["nex"]]
        linhas.append("Pelo NEX, a ficha deve ter: " + "; ".join(ganhos))
    return linhas


# ------------------------------------------------------------------ D&D 5e (Livro do Jogador)
DND_CLASSES = {  # (testes de resistência, perícias da classe a escolher, página)
    "barbaro": (("forca", "constituicao"), 2, 47), "bardo": (("destreza", "carisma"), 3, 52),
    "bruxo": (("sabedoria", "carisma"), 2, 58), "clerigo": (("sabedoria", "carisma"), 2, 64),
    "druida": (("inteligencia", "sabedoria"), 2, 73), "feiticeiro": (("constituicao", "carisma"), 2, 78),
    "guerreiro": (("forca", "constituicao"), 2, 84), "ladino": (("destreza", "inteligencia"), 4, 90),
    "mago": (("inteligencia", "sabedoria"), 2, 95), "monge": (("forca", "destreza"), 2, 103),
    "paladino": (("sabedoria", "carisma"), 2, 110), "patrulheiro": (("forca", "destreza"), 3, 116),
    "artifice": (("constituicao", "inteligencia"), 2, None),
}
# Espaços de magia do conjurador completo por nível (tabelas das classes)
COMPLETO = {1: [2], 2: [3], 3: [4, 2], 4: [4, 3], 5: [4, 3, 2], 6: [4, 3, 3], 7: [4, 3, 3, 1], 8: [4, 3, 3, 2],
            9: [4, 3, 3, 3, 1], 10: [4, 3, 3, 3, 2], 11: [4, 3, 3, 3, 2, 1], 12: [4, 3, 3, 3, 2, 1],
            13: [4, 3, 3, 3, 2, 1, 1], 14: [4, 3, 3, 3, 2, 1, 1], 15: [4, 3, 3, 3, 2, 1, 1, 1],
            16: [4, 3, 3, 3, 2, 1, 1, 1], 17: [4, 3, 3, 3, 2, 1, 1, 1, 1], 18: [4, 3, 3, 3, 3, 1, 1, 1, 1],
            19: [4, 3, 3, 3, 3, 2, 1, 1, 1], 20: [4, 3, 3, 3, 3, 2, 2, 1, 1]}
PACTO = {1: (1, 1), 2: (2, 1), 3: (2, 2), 4: (2, 2), 5: (2, 3), 6: (2, 3), 7: (2, 4), 8: (2, 4), 9: (2, 5),
         10: (2, 5), **{n: (3, 5) for n in range(11, 17)}, **{n: (4, 5) for n in range(17, 21)}}


def classe_dnd(s):
    for palavra in re.findall(r"[a-z]+", plain(s["classe"])):
        if palavra in DND_CLASSES:
            return palavra
        if palavra == "guardiao":
            return "patrulheiro"
    return None


def espacos_esperados(cls, nivel):
    """{círculo: quantidade} dos espaços de magia da classe no nível, ou None se não conjura."""
    if cls in ("bardo", "clerigo", "druida", "feiticeiro", "mago"):
        return dict(enumerate(COMPLETO[nivel], 1))
    if cls in ("paladino", "patrulheiro"):
        return dict(enumerate(COMPLETO[math.ceil(nivel / 2)], 1)) if nivel >= 2 else {}
    if cls == "artifice":
        return dict(enumerate(COMPLETO[math.ceil(nivel / 2)], 1))
    if cls == "bruxo":
        qtd, circulo = PACTO[nivel]
        return {circulo: qtd}
    return None


def conferir_dnd(s, avisos):
    cls, nivel = classe_dnd(s), s["nivel"]
    if "/" in s["classe"]:
        avisos.append("Multiclasse: confira à mão PV, testes de resistência e espaços de magia (p. 163-165).")
    if cls is None:
        avisos.append(f"Classe '{s['classe']}' não reconhecida (Livro do Jogador, cap. 3).")
    for attr, info in s["atributos"].items():
        if info["valor"] > 20:
            avisos.append(f"{dnd.NOMES[attr]} {info['valor']}: o máximo para personagens é 20 (p. 173).")
    if not s["raca"]:
        avisos.append("Falta a raça (cap. 2).")
    if not s["antecedente"]:
        avisos.append("Falta o antecedente (cap. 4).")
    if cls is None or "/" in s["classe"]:
        return
    salvas, n_pericias, _ = DND_CLASSES[cls]
    marcadas = {k for k, r in s["resistencia"].items() if r["proficiente"]}
    if marcadas != set(salvas):
        avisos.append(f"Testes de resistência proficientes: {sorted(marcadas)}; a classe dá {list(salvas)}.")
    profs = [k for k, p in s["pericias"].items() if p["grau"] >= 1]
    if len(profs) < n_pericias + 2:
        avisos.append(f"{len(profs)} perícias proficientes; o mínimo é {n_pericias + 2} ({n_pericias} da classe + "
                      "2 do antecedente; algumas raças dão mais).")
    dado = int(dnd.DADO_VIDA_POR_CLASSE[cls][1:])
    con = dnd.mod(s, "constituicao")
    fixo = dado + con + (nivel - 1) * (dado // 2 + 1 + con)
    extra_raca = nivel if "colina" in plain(s["raca"]) else 0  # Tenacidade Anã (p. 20)
    if s["combate"]["hp_max"] != fixo + extra_raca:
        avisos.append(f"PV máximo {s['combate']['hp_max']}; pela regra fixa seria {fixo + extra_raca} "
                      f"(d{dado} cheio no 1º nível + CON, depois {dado // 2 + 1} + CON por nível, p. 12 e 15"
                      + (", + Tenacidade Anã" if extra_raca else "") + "). Se os PV foram rolados, ignore.")
    esperados = espacos_esperados(cls, nivel)
    if esperados is not None:
        tem = {int(c): sl["max"] for c, sl in s["magias"]["slots"].items() if sl["max"]}
        if tem != esperados:
            avisos.append(f"Espaços de magia {tem or 'nenhum'}; a classe no nível {nivel} tem {esperados}.")
        if not s["magias"]["lista"] and esperados:
            avisos.append("Conjurador sem magias na lista.")
    if not s["caracteristicas"]:
        avisos.append("Nenhuma característica anotada (classe, raça, antecedente).")
    if not s["combate"]["dados_vida"]["dado"]:
        avisos.append("Dado de vida vazio.")


def resumo_dnd(s):
    attrs = "  ".join(f"{sig} {s['atributos'][k]['valor']} ({s['atributos'][k]['mod']:+d})"
                      for k, sig, _ in dnd.ATRIBUTOS)
    profs = [nome + (" (especialista)" if s["pericias"][k]["grau"] == 2 else "") + f" {s['pericias'][k]['bonus']:+d}"
             for k, nome, _ in dnd.PERICIAS if s["pericias"][k]["grau"]]
    salvas = [f"{dnd.NOMES[k]} {r['bonus']:+d}" for k, r in s["resistencia"].items() if r["proficiente"]]
    c = s["combate"]
    linhas = [
        f"{s['nome']} — {s['raca'] or '?'} {s['classe'] or '?'} {s['nivel']}, antecedente {s['antecedente'] or '?'}",
        f"Atributos: {attrs}",
        f"PV {c['hp_max']}  CA {c['ca']}  Iniciativa {c['iniciativa']:+d}  Deslocamento {c['deslocamento']}  "
        f"Proficiência +{c['proficiencia']}  Percepção passiva {c['percepcao_passiva']}  Dado de vida "
        f"{s['nivel']}{c['dados_vida']['dado']}",
        f"Resistências: {', '.join(salvas) or '—'}",
        f"Perícias ({len(profs)}): {', '.join(profs)}",
    ]
    if s["magias"]["lista"] or any(sl["max"] for sl in s["magias"]["slots"].values()):
        slots = {c_: sl["max"] for c_, sl in s["magias"]["slots"].items() if sl["max"]}
        linhas.append(f"Magia: CD {s['magias']['cd_salvamento']}, ataque {s['magias']['bonus_ataque']:+d}, "
                      f"espaços {slots}, {len(s['magias']['lista'])} magias")
    if s["ataques"]:
        linhas.append("Ataques: " + ", ".join(f"{a['nome']} {a['ataque']} {a['dano']}" for a in s["ataques"]))
    if s["caracteristicas"]:
        linhas.append("Características: " + ", ".join(f["nome"] for f in s["caracteristicas"]))
    return linhas


# ------------------------------------------------------------------ principal
def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("escolhas")
    ap.add_argument("--saida")
    ap.add_argument("--conferir", action="store_true", help="só confere, não salva")
    ap.add_argument("--sobrescrever", action="store_true")
    args = ap.parse_args()

    with open(args.escolhas, encoding="utf-8") as f:
        bruto = json.load(f)
    sistema = bruto.setdefault("sistema", dnd.SYSTEM)  # como no app: sem sistema, é D&D
    if sistema not in (ordem.SYSTEM, dnd.SYSTEM):
        sys.exit('"sistema" deve ser "ordem" ou "dnd5e".')
    tabela = ordem.PERICIAS if sistema == ordem.SYSTEM else dnd.PERICIAS
    bruto["pericias"] = chaves_pericias(bruto.get("pericias"), tabela)
    desconhecidas = [k for k in (bruto.get("pericias") or {}) if k not in {t[0] for t in tabela}]
    if sistema == dnd.SYSTEM:  # ficha nova: espaços de magia e recursos começam cheios
        for slot in ((bruto.get("magias") or {}).get("slots") or {}).values():
            if isinstance(slot, dict) and "atual" not in slot:
                slot["atual"] = slot.get("max", 0)
        for r in bruto.get("recursos") or []:
            if isinstance(r, dict) and "atual" not in r:
                r["atual"] = r.get("max", 0)

    ficha = sheet_io.normalize_sheet(bruto)
    avisos = [f"Perícias não reconhecidas (ignoradas): {', '.join(desconhecidas)}."] if desconhecidas else []
    if sistema == ordem.SYSTEM:
        conferir_ordem(ficha, avisos)
        linhas = resumo_ordem(ficha)
    else:
        conferir_dnd(ficha, avisos)
        linhas = resumo_dnd(ficha)

    print("\n".join(linhas))
    print("\nAVISOS:" if avisos else "\nSem avisos: a ficha segue as regras de criação.")
    for a in avisos:
        print(f"- {a}")

    if not args.conferir:
        saida = args.saida or os.path.join(RAIZ, "sheets", nome_arquivo(ficha["nome"]) + ".json")
        if os.path.exists(saida) and not args.sobrescrever:
            sys.exit(f"\n{saida} já existe. Use --sobrescrever ou --saida.")
        sheet_io.save_sheet(ficha, saida)
        print(f"\nSalva em {os.path.relpath(saida, RAIZ)}")
    sys.exit(2 if avisos else 0)


if __name__ == "__main__":
    main()
