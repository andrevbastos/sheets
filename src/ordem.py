"""Ficha de Ordem Paranormal: perícias, regras automáticas e normalização.

As regras vêm do livro básico (páginas citadas em cada função). `apply_rules(sheet)` grava os
valores derivados na própria ficha, então o JSON salvo e o que a rede envia já vêm calculados.
"""
import copy
import unicodedata

SYSTEM = "ordem"

ATRIBUTOS = [("agi", "AGI", "Agilidade"), ("for", "FOR", "Força"), ("int", "INT", "Intelecto"),
             ("pre", "PRE", "Presença"), ("vig", "VIG", "Vigor")]

# (chave, nome, atributo, somente treinada, penalidade de carga)
PERICIAS = [
    ("acrobacia", "Acrobacia", "agi", False, True),
    ("adestramento", "Adestramento", "pre", True, False),
    ("artes", "Artes", "pre", True, False),
    ("atletismo", "Atletismo", "for", False, False),
    ("atualidades", "Atualidades", "int", False, False),
    ("ciencias", "Ciências", "int", True, False),
    ("crime", "Crime", "agi", True, True),
    ("diplomacia", "Diplomacia", "pre", False, False),
    ("enganacao", "Enganação", "pre", False, False),
    ("fortitude", "Fortitude", "vig", False, False),
    ("furtividade", "Furtividade", "agi", False, True),
    ("iniciativa", "Iniciativa", "agi", False, False),
    ("intimidacao", "Intimidação", "pre", False, False),
    ("intuicao", "Intuição", "pre", False, False),
    ("investigacao", "Investigação", "int", False, False),
    ("luta", "Luta", "for", False, False),
    ("medicina", "Medicina", "int", False, False),
    ("ocultismo", "Ocultismo", "int", True, False),
    ("percepcao", "Percepção", "pre", False, False),
    ("pilotagem", "Pilotagem", "agi", True, False),
    ("pontaria", "Pontaria", "agi", False, False),
    ("profissao", "Profissão", "int", True, False),
    ("reflexos", "Reflexos", "agi", False, False),
    ("religiao", "Religião", "pre", True, False),
    ("sobrevivencia", "Sobrevivência", "int", False, False),
    ("tatica", "Tática", "int", True, False),
    ("tecnologia", "Tecnologia", "int", True, False),
    ("vontade", "Vontade", "pre", False, False),
]
PERICIAS_CARGA = {key for key, _, _, _, carga in PERICIAS if carga}

RECURSOS = [("pv", "PV", "Pontos de Vida"), ("pe", "PE", "Pontos de Esforço"), ("san", "SAN", "Sanidade")]
CATEGORIAS = ["I", "II", "III", "IV"]
DESCRICAO = [("aparencia", "Aparência"), ("personalidade", "Personalidade"),
             ("historico", "Histórico"), ("objetivo", "Objetivo")]

# Grau de treinamento (p. 50)
GRAUS = [(0, "Destreinado"), (5, "Treinado"), (10, "Veterano"), (15, "Expert")]

# Classes (p. 35, 39, 43): (inicial, por NEX, atributo somado em ambos)
CLASSES = {
    "combatente": {"nome": "Combatente", "pv": (20, 4, "vig"), "pe": (2, 2, "pre"), "san": (12, 3, None)},
    "especialista": {"nome": "Especialista", "pv": (16, 3, "vig"), "pe": (3, 3, "pre"), "san": (16, 4, None)},
    "ocultista": {"nome": "Ocultista", "pv": (12, 2, "vig"), "pe": (4, 4, "pre"), "san": (20, 5, None)},
}

# Níveis de exposição válidos (Tabela 1.2, p. 33)
NEX_LEVELS = list(range(5, 100, 5)) + [99]

# Tabela 3.1: Patentes (p. 62): (PP mínimo, patente, crédito, limites I..IV)
PATENTES = [
    (0, "Recruta", "Baixo", (2, 0, 0, 0)),
    (20, "Operador", "Médio", (3, 1, 0, 0)),
    (50, "Agente especial", "Médio", (3, 2, 1, 0)),
    (100, "Oficial de operações", "Alto", (3, 3, 2, 1)),
    (200, "Agente de elite", "Ilimitado", (3, 3, 3, 2)),
]


# ------------------------------------------------------------------ regras
def _plain(text) -> str:
    text = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode()
    return text.strip().lower()


def class_key(sheet):
    """Chave da classe ("combatente"...) ou None se for outra/vazia."""
    name = _plain(sheet.get("classe"))
    for key in CLASSES:
        if name.startswith(key[:6]):
            return key
    return None


def nex_valido(nex: int) -> int:
    """Arredonda para o nível de exposição válido mais próximo (5%, 10%, ..., 95%, 99%)."""
    return min(NEX_LEVELS, key=lambda level: (abs(level - nex), -level))


def nex_nivel(sheet) -> int:
    """Quantos níveis de exposição o personagem tem (5% = 1, 99% = 20)."""
    return NEX_LEVELS.index(nex_valido(sheet.get("nex", 5))) + 1


def limite_pe(sheet) -> int:
    """Limite de PE por turno (Tabela 1.2, p. 33): igual ao nível de exposição."""
    return nex_nivel(sheet)


def recurso_calculado(sheet, key):
    """Máximo de PV/PE/SAN pela classe, NEX e atributo (p. 33-43), ou None se a classe é outra."""
    cls = class_key(sheet)
    if cls is None:
        return None
    inicial, por_nex, attr = CLASSES[cls][key]
    bonus_attr = sheet["atributos"].get(attr, 0) if attr else 0
    niveis_extras = nex_nivel(sheet) - 1
    return inicial + bonus_attr + niveis_extras * (por_nex + bonus_attr)


def dt_rituais(sheet) -> int:
    """DT para resistir aos rituais (p. 131): 10 + limite de PE + Presença."""
    return 10 + limite_pe(sheet) + sheet["atributos"].get("pre", 0)


def carga_maxima(sheet) -> int:
    """Espaços de itens (p. 63): 5 por ponto de Força; com Força 0, apenas 2."""
    forca = sheet["atributos"].get("for", 0)
    return 5 * forca if forca > 0 else 2


def espacos_usados(sheet) -> int:
    return sum(item.get("espacos", 0) for item in sheet.get("inventario", {}).get("itens", []))


def sobrecarregado(sheet) -> bool:
    return espacos_usados(sheet) > sheet.get("inventario", {}).get("carga_max", 0)


def patente(sheet):
    """(patente, crédito, limites) pelos pontos de prestígio (Tabela 3.1, p. 62)."""
    pp = sheet.get("inventario", {}).get("pontos_prestigio", 0)
    atual = PATENTES[0]
    for row in PATENTES:
        if pp >= row[0]:
            atual = row
    return atual[1], atual[2], dict(zip(CATEGORIAS, atual[3]))


def itens_por_categoria(sheet) -> dict:
    counts = {c: 0 for c in CATEGORIAS}
    for item in sheet.get("inventario", {}).get("itens", []):
        cat = str(item.get("categoria", "")).strip().upper()
        if cat in counts:
            counts[cat] += 1
    return counts


def defesa_total(sheet) -> int:
    """Defesa (p. 46): 10 + AGI + equipamento + outros; sobrecarregado sofre −5 (p. 63)."""
    d = sheet.get("defesa", {})
    total = 10 + sheet.get("atributos", {}).get("agi", 0) + d.get("equipamento", 0) + d.get("outros", 0)
    return total - 5 if sobrecarregado(sheet) else total


def bonus_pericia(sheet, key) -> int:
    """Grau de treino + outros; perícias de carga sofrem −5 quando sobrecarregado (p. 63)."""
    p = sheet.get("pericias", {}).get(key, {})
    total = p.get("treino", 0) + p.get("outros", 0)
    if key in PERICIAS_CARGA and sobrecarregado(sheet):
        total -= 5
    return total


def dados(sheet, attr) -> str:
    """Dados do teste (p. 24): 1d20 por ponto do atributo; atributo 0 rola 2d20 e fica com o pior."""
    valor = sheet.get("atributos", {}).get(attr, 0)
    return f"{valor}d20" if valor > 0 else "2d20↓"


def apply_rules(sheet: dict) -> dict:
    """Grava na ficha (no lugar) tudo o que as regras definem. Devolve a própria ficha."""
    sheet["nex"] = nex_valido(sheet.get("nex", 5))
    sheet["pe_rodada"] = limite_pe(sheet)
    sheet["dt_rituais"] = dt_rituais(sheet)

    for key, _, _ in RECURSOS:
        res = sheet[key]
        calculado = recurso_calculado(sheet, key)
        if calculado is not None:
            antigo_max = res["max"]
            res["max"] = max(0, calculado + res.get("bonus", 0))
            if antigo_max == 0 and res["atual"] == 0:
                res["atual"] = res["max"]  # ficha nova: começa cheia
            elif antigo_max > 0 and res["atual"] >= antigo_max:
                res["atual"] = res["max"]  # estava cheio: continua cheio quando o máximo muda
        res["atual"] = max(0, min(res["atual"], res["max"]))

    inv = sheet["inventario"]
    inv["carga_max"] = carga_maxima(sheet)
    inv["patente"], inv["limite_credito"], inv["limite_itens"] = patente(sheet)
    return sheet


def normalize(sheet: dict, to_int, clean_list) -> dict:
    s = copy.deepcopy(sheet)
    s["sistema"] = SYSTEM
    s["nome"] = str(s.get("nome") or "Sem Nome")
    cor = str(s.get("cor") or "").strip()
    s["cor"] = cor if cor.startswith("#") and len(cor) in (4, 7) else "#8e44ad"
    for key in ("jogador", "origem", "classe", "deslocamento", "protecao", "resistencias"):
        s[key] = str(s.get(key) or "")
    if not s["deslocamento"]:
        s["deslocamento"] = "9m"
    s["nex"] = to_int(s.get("nex"), 5)

    attrs = s.get("atributos") if isinstance(s.get("atributos"), dict) else {}
    s["atributos"] = {key: max(0, to_int(attrs.get(key), 1)) for key, _, _ in ATRIBUTOS}

    for key, _, _ in RECURSOS:
        res = s.get(key) if isinstance(s.get(key), dict) else {}
        maximo = max(0, to_int(res.get("max"), 0))
        # o "atual" só é limitado ao máximo depois de as regras recalcularem o máximo (apply_rules)
        s[key] = {"max": maximo, "atual": max(0, to_int(res.get("atual"), maximo)),
                  "bonus": to_int(res.get("bonus"), 0)}

    d = s.get("defesa") if isinstance(s.get("defesa"), dict) else {}
    s["defesa"] = {"equipamento": to_int(d.get("equipamento"), 0), "outros": to_int(d.get("outros"), 0)}

    graus = [g for g, _ in GRAUS]
    per = s.get("pericias") if isinstance(s.get("pericias"), dict) else {}
    s["pericias"] = {}
    for key, *_ in PERICIAS:
        p = per.get(key) if isinstance(per.get(key), dict) else {}
        treino = to_int(p.get("treino"), 0)
        treino = max(g for g in graus if g <= max(0, min(treino, 15)))  # só 0/5/10/15
        s["pericias"][key] = {"treino": treino, "outros": to_int(p.get("outros"), 0)}
    s["profissao_nome"] = str(s.get("profissao_nome") or "")

    s["ataques"] = [
        {k: str(a.get(k) or "") for k in ("nome", "teste", "dano", "especial")}
        for a in clean_list(s.get("ataques")) if isinstance(a, dict)
    ]
    s["habilidades"] = [
        {"nome": str(h.get("nome") or ""), "custo": str(h.get("custo") or ""),
         "pagina": str(h.get("pagina") or ""), "descricao": str(h.get("descricao") or "")}
        for h in clean_list(s.get("habilidades")) if isinstance(h, dict)
    ]

    inv = s.get("inventario") if isinstance(s.get("inventario"), dict) else {}
    s["inventario"] = {
        "pontos_prestigio": max(0, to_int(inv.get("pontos_prestigio"), 0)),
        "itens": [
            {"nome": str(i.get("nome") or ""), "categoria": str(i.get("categoria") or ""),
             "espacos": max(0, to_int(i.get("espacos"), 0))}
            for i in clean_list(inv.get("itens")) if isinstance(i, dict)
        ],
    }

    desc = s.get("descricao") if isinstance(s.get("descricao"), dict) else {}
    s["descricao"] = {key: str(desc.get(key) or "") for key, _ in DESCRICAO}
    return apply_rules(s)
