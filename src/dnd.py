"""Ficha de D&D 5e: atributos, perícias, regras automáticas e normalização.

As regras vêm do Livro do Jogador em português (sistemas/dnd-5e/regras-jogador.pdf; páginas
impressas citadas em cada função). `apply_rules(sheet)` grava os valores derivados na própria
ficha, então o JSON salvo e o que a rede envia já vêm calculados.

Fichas antigas (antes das regras automáticas) guardavam o bônus final de cada perícia. Ao abrir,
a diferença entre esse bônus e o calculado vira o campo "outros", para nenhum número mudar.
"""
import copy
import re
import unicodedata

SYSTEM = "dnd5e"

# (chave, sigla, nome)
ATRIBUTOS = [("forca", "FOR", "Força"), ("destreza", "DES", "Destreza"), ("constituicao", "CON", "Constituição"),
             ("inteligencia", "INT", "Inteligência"), ("sabedoria", "SAB", "Sabedoria"), ("carisma", "CAR", "Carisma")]

# Perícias por habilidade (p. 174). As chaves antigas das fichas ficam ("blefar" = Enganação).
PERICIAS = [
    ("acrobacia", "Acrobacia", "destreza"),
    ("adestramento", "Adestrar Animais", "sabedoria"),
    ("arcanismo", "Arcanismo", "inteligencia"),
    ("atletismo", "Atletismo", "forca"),
    ("atuacao", "Atuação", "carisma"),
    ("blefar", "Enganação", "carisma"),
    ("furtividade", "Furtividade", "destreza"),
    ("historia", "História", "inteligencia"),
    ("intimidacao", "Intimidação", "carisma"),
    ("intuicao", "Intuição", "sabedoria"),
    ("investigacao", "Investigação", "inteligencia"),
    ("medicina", "Medicina", "sabedoria"),
    ("natureza", "Natureza", "inteligencia"),
    ("percepcao", "Percepção", "sabedoria"),
    ("persuasao", "Persuasão", "carisma"),
    ("prestidigitacao", "Prestidigitação", "destreza"),
    ("religiao", "Religião", "inteligencia"),
    ("sobrevivencia", "Sobrevivência", "sabedoria"),
]
PERICIA_ATRIBUTO = {key: attr for key, _, attr in PERICIAS}

# Grau na perícia: 0 = sem proficiência, 1 = proficiente, 2 = especialista (dobra o bônus, p. 173-174)
GRAUS = [(0, "—"), (1, "Proficiente"), (2, "Especialista")]

# Atributo de conjuração de cada classe (capítulo de cada classe; CD na p. 205)
CONJURACAO_POR_CLASSE = {
    "artifice": "inteligencia", "mago": "inteligencia",
    "bardo": "carisma", "bruxo": "carisma", "feiticeiro": "carisma", "paladino": "carisma",
    "clerigo": "sabedoria", "druida": "sabedoria", "patrulheiro": "sabedoria", "guardiao": "sabedoria",
}

NIVEL_MAX = 20


def _plain(text) -> str:
    text = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode()
    return text.strip().lower()


# ------------------------------------------------------------------ regras
def modificador(valor: int) -> int:
    """Modificador do valor de habilidade (tabela da p. 173): 10-11 = +0, 12-13 = +1, 8-9 = −1..."""
    return (valor - 10) // 2


def mod(sheet, attr) -> int:
    return modificador(sheet["atributos"][attr]["valor"])


def bonus_proficiencia(nivel: int) -> int:
    """Bônus de proficiência pelo nível (tabela Avanço de Personagem, p. 15): +2 no 1º, +6 no 17º."""
    nivel = max(1, min(nivel, NIVEL_MAX))
    return 2 + (nivel - 1) // 4


def prof(sheet) -> int:
    return bonus_proficiencia(sheet.get("nivel", 1))


def bonus_pericia(sheet, key) -> int:
    """Modificador do atributo + proficiência (dobrada se especialista) + outros (p. 173-174)."""
    p = sheet["pericias"][key]
    return mod(sheet, PERICIA_ATRIBUTO[key]) + p["grau"] * prof(sheet) + p["outros"]


def bonus_resistencia(sheet, attr) -> int:
    """Teste de resistência: modificador + proficiência se proficiente (p. 179) + outros."""
    r = sheet["resistencia"][attr]
    return mod(sheet, attr) + (prof(sheet) if r["proficiente"] else 0) + r["outros"]


def iniciativa(sheet) -> int:
    """Iniciativa é um teste de Destreza (p. 189) + outros (talentos, características)."""
    return mod(sheet, "destreza") + sheet["combate"]["iniciativa_outros"]


def percepcao_passiva(sheet) -> int:
    """Sabedoria (Percepção) passiva: 10 + todos os bônus do teste (p. 175 e 177)."""
    return 10 + bonus_pericia(sheet, "percepcao")


def atributo_conjuracao(sheet):
    """Atributo de conjuração escolhido ou, se vazio, o da classe conjuradora/classe. None se não há."""
    magias = sheet.get("magias", {})
    if magias.get("atributo") in {attr for attr, *_ in ATRIBUTOS}:
        return magias["atributo"]
    for texto in (magias.get("classe_conjurador"), sheet.get("classe")):
        palavras = re.findall(r"[a-z]+", _plain(texto))
        for palavra in palavras:
            if palavra in CONJURACAO_POR_CLASSE:
                return CONJURACAO_POR_CLASSE[palavra]
    return None


def cd_magia(sheet):
    """CD para resistir às magias: 8 + modificador de conjuração + proficiência (p. 205). None sem atributo."""
    attr = atributo_conjuracao(sheet)
    return None if attr is None else 8 + mod(sheet, attr) + prof(sheet)


def ataque_magia(sheet):
    """Bônus de ataque mágico: modificador de conjuração + proficiência (p. 205). None sem atributo."""
    attr = atributo_conjuracao(sheet)
    return None if attr is None else mod(sheet, attr) + prof(sheet)


# ------------------------------------------------------------------ rolagens
NOMES = {attr: nome for attr, _, nome in ATRIBUTOS}
_POR_SIGLA = {sigla: attr for attr, sigla, _ in ATRIBUTOS}
_SIGLA_RE = re.compile(r"(?<![A-Za-zÀ-ÿ])(FOR|DES|CON|INT|SAB|CAR)(?![A-Za-zÀ-ÿ])", re.I)
_NUM_RE = re.compile(r"([+\-−]?)\s*(\d+)")


def teste_request(bonus: int, label: str) -> dict:
    """Teste de d20: 1d20 + bônus (vantagem/desvantagem com Shift/Ctrl na ficha)."""
    return {"sides": 20, "qty": 1, "mode": "normal", "extra": 0, "bonus": bonus, "label": label}


def pericia_request(sheet, key) -> dict:
    return teste_request(bonus_pericia(sheet, key), next(n for k, n, _ in PERICIAS if k == key))


def resistencia_request(sheet, attr) -> dict:
    return teste_request(bonus_resistencia(sheet, attr), f"Resistência de {NOMES[attr]}")


def atributo_request(sheet, attr) -> dict:
    return teste_request(mod(sheet, attr), f"Teste de {NOMES[attr]}")


def iniciativa_request(sheet, label=None) -> dict:
    return teste_request(iniciativa(sheet), label or f"{sheet.get('nome', '')} · Iniciativa")


def ataque_magia_request(sheet):
    bonus = ataque_magia(sheet)
    if bonus is None:
        bonus = sheet["magias"]["bonus_ataque"]
    return teste_request(bonus, "Ataque mágico")


def ataque_request(sheet, text, label="Ataque"):
    """Jogada de ataque escrita à mão: '+5', '5', 'FOR' ou 'DES +1' (atributo + proficiência + extra).

    Com a sigla, conta proficiência na arma (p. 194); para arma sem proficiência, escreva o número.
    None se o texto estiver vazio ou não tiver número nem atributo.
    """
    text = str(text or "").strip()
    sigla = _SIGLA_RE.search(text)
    numeros = [int(n) * (-1 if s in ("-", "−") else 1) for s, n in _NUM_RE.findall(_SIGLA_RE.sub("", text))]
    if sigla:
        return teste_request(mod(sheet, _POR_SIGLA[sigla.group(1).upper()]) + prof(sheet) + sum(numeros), label)
    if numeros:
        return teste_request(sum(numeros), label)
    return None


def dano_request(sheet, text, label="Dano"):
    """Dano: '2d6+3 cortante', '1d8+FOR' (a sigla vira o modificador). None sem dados."""
    from src import dice  # tardio: dice não precisa das regras de D&D

    def troca(match):
        valor = mod(sheet, _POR_SIGLA[match.group(2).upper()])
        if match.group(1) in ("-", "−"):
            valor = -valor
        return f"{'+' if valor >= 0 else '-'}{abs(valor)}"

    texto = re.sub(r"([+\-−])\s*(FOR|DES|CON|INT|SAB|CAR)(?![A-Za-zÀ-ÿ])", troca, str(text or ""), flags=re.I)
    req = dice.parse_dice(texto)
    return {**req, "label": label} if req else None


def apply_rules(sheet: dict) -> dict:
    """Grava na ficha (no lugar) tudo o que as regras definem. Devolve a própria ficha."""
    sheet["nivel"] = max(1, min(sheet.get("nivel", 1), NIVEL_MAX))
    for attr, *_ in ATRIBUTOS:
        sheet["atributos"][attr]["mod"] = mod(sheet, attr)
    for key, *_ in PERICIAS:
        p = sheet["pericias"][key]
        p["proficiente"] = p["grau"] > 0
        p["bonus"] = bonus_pericia(sheet, key)
    for attr, *_ in ATRIBUTOS:
        sheet["resistencia"][attr]["bonus"] = bonus_resistencia(sheet, attr)
    combate = sheet["combate"]
    combate["proficiencia"] = prof(sheet)
    combate["iniciativa"] = iniciativa(sheet)
    combate["percepcao_passiva"] = percepcao_passiva(sheet)
    combate["hp_atual"] = max(0, min(combate["hp_atual"], combate["hp_max"]))
    magias = sheet["magias"]
    if atributo_conjuracao(sheet) is not None:  # sem atributo, CD e bônus ficam como digitados
        magias["cd_salvamento"], magias["bonus_ataque"] = cd_magia(sheet), ataque_magia(sheet)
    return sheet


# ------------------------------------------------------------------ normalização
def _classe_e_nivel(s, to_int):
    """Fichas antigas têm "classe_nivel" ("Guerreiro 3 / Mago 2"): separa em classe e nível total."""
    if "classe" in s or "classe_nivel" not in s:
        return str(s.get("classe") or ""), to_int(s.get("nivel"), 1)
    texto = str(s.pop("classe_nivel") or "")
    numeros = [int(n) for n in re.findall(r"\d+", texto)]
    classe = re.sub(r"\s+", " ", re.sub(r"\d+", "", texto)).strip(" /-,")
    return classe, sum(numeros) or 1


_ANTIGO_RE = re.compile(r"^\s*B[ôo]nus:\s*([+\-−]?\s*\d+)\s*\|\s*Dano:\s*(.+?)\s*$", re.I)


def _ataque(a) -> dict:
    """Ataque com campos próprios de ataque e dano. Os antigos ("Bônus: +5 | Dano: 2d6+3 (Cortante)")
    são separados nesses campos."""
    ataque, dano, descricao = str(a.get("ataque") or ""), str(a.get("dano") or ""), str(a.get("descricao") or "")
    if "ataque" not in a and "dano" not in a:
        antigo = _ANTIGO_RE.match(descricao)
        if antigo:
            ataque, dano, descricao = antigo.group(1).replace(" ", ""), antigo.group(2), ""
    return {"nome": str(a.get("nome") or ""), "ataque": ataque, "dano": dano, "descricao": descricao}


def _lista_para_texto(value) -> str:
    """Idiomas e proficiências viraram texto livre (antes eram listas)."""
    if isinstance(value, list):
        return ", ".join(str(v).strip() for v in value if str(v).strip())
    return str(value or "")


def normalize(sheet: dict, to_int, to_bool, clean_list) -> dict:
    s = copy.deepcopy(sheet) if isinstance(sheet, dict) else {}
    s["sistema"] = SYSTEM
    s["nome"] = str(s.get("nome") or "Sem Nome")
    cor = str(s.get("cor") or "").strip()
    s["cor"] = cor if cor.startswith("#") and len(cor) in (4, 7) else "#d4af37"
    s["classe"], s["nivel"] = _classe_e_nivel(s, to_int)
    s.pop("classe_nivel", None)
    for key in ("jogador", "raca", "antecedente", "tendencia"):
        s[key] = str(s.get(key) or "")
    s["experiencia"] = max(0, to_int(s.get("experiencia"), 0))
    nivel = max(1, min(s["nivel"], NIVEL_MAX))
    pb = bonus_proficiencia(nivel)

    attrs = s.get("atributos") if isinstance(s.get("atributos"), dict) else {}
    s["atributos"] = {}
    for attr, *_ in ATRIBUTOS:
        a = attrs.get(attr) if isinstance(attrs.get(attr), dict) else {}
        s["atributos"][attr] = {"valor": max(1, min(to_int(a.get("valor"), 10), 30))}
    mods = {attr: modificador(s["atributos"][attr]["valor"]) for attr, *_ in ATRIBUTOS}

    per = s.get("pericias") if isinstance(s.get("pericias"), dict) else {}
    s["pericias"] = {}
    for key, _, attr in PERICIAS:
        p = per.get(key) if isinstance(per.get(key), dict) else {}
        grau = to_int(p.get("grau"), 2 if to_bool(p.get("especialista")) else 1 if to_bool(p.get("proficiente")) else 0)
        grau = max(0, min(grau, 2))
        if "outros" in p:
            outros = to_int(p.get("outros"), 0)
        else:  # ficha antiga: guarda a diferença para o bônus continuar igual
            outros = to_int(p.get("bonus"), mods[attr] + grau * pb) - (mods[attr] + grau * pb)
        s["pericias"][key] = {"grau": grau, "outros": outros}

    res = s.get("resistencia") if isinstance(s.get("resistencia"), dict) else {}
    s["resistencia"] = {}
    for attr, *_ in ATRIBUTOS:
        r = res.get(attr) if isinstance(res.get(attr), dict) else {}
        proficiente = to_bool(r.get("proficiente"))
        calculado = mods[attr] + (pb if proficiente else 0)
        outros = to_int(r.get("outros"), 0) if "outros" in r else to_int(r.get("bonus"), calculado) - calculado
        s["resistencia"][attr] = {"proficiente": proficiente, "outros": outros}

    c = s.get("combate") if isinstance(s.get("combate"), dict) else {}
    hp_max = max(0, to_int(c.get("hp_max"), 0))
    ini_outros = (to_int(c.get("iniciativa_outros"), 0) if "iniciativa_outros" in c
                  else to_int(c.get("iniciativa"), mods["destreza"]) - mods["destreza"])
    s["combate"] = {"hp_max": hp_max, "hp_atual": max(0, to_int(c.get("hp_atual"), hp_max)),
                    "ca": to_int(c.get("ca"), 10), "iniciativa_outros": ini_outros,
                    "deslocamento": str(c.get("deslocamento") or "9m")}

    magias = s.get("magias") if isinstance(s.get("magias"), dict) else {}
    atributo = magias.get("atributo") if magias.get("atributo") in mods else ""
    slots = magias.get("slots") if isinstance(magias.get("slots"), dict) else {}
    s["magias"] = {
        "classe_conjurador": str(magias.get("classe_conjurador") or ""),
        "atributo": atributo,
        "cd_salvamento": to_int(magias.get("cd_salvamento"), 8),
        "bonus_ataque": to_int(magias.get("bonus_ataque"), 0),
        "slots": {},
        "lista": [{"nome": str(m.get("nome") or ""), "descricao": str(m.get("descricao") or "")}
                  for m in clean_list(magias.get("lista")) if isinstance(m, dict)],
    }
    for lvl in range(1, 10):
        slot = slots.get(str(lvl)) if isinstance(slots.get(str(lvl)), dict) else {}
        maximo = max(0, to_int(slot.get("max"), 0))
        s["magias"]["slots"][str(lvl)] = {"atual": max(0, min(to_int(slot.get("atual"), 0), maximo)), "max": maximo}

    s["ataques"] = [_ataque(a) for a in clean_list(s.get("ataques")) if isinstance(a, dict)]
    s["caracteristicas"] = [{"nome": str(f.get("nome") or ""), "detalhes": str(f.get("detalhes") or "")}
                            for f in clean_list(s.get("caracteristicas")) if isinstance(f, dict)]
    s["idiomas"] = _lista_para_texto(s.get("idiomas"))
    s["proficiencias"] = _lista_para_texto(s.get("proficiencias"))
    s["recursos"] = clean_list(s.get("recursos"))
    s["inventario"] = [str(item) for item in clean_list(s.get("inventario"))]

    # Fichas antigas usavam "custom" no lugar de "extra"
    extra = s.get("extra")
    if not isinstance(extra, dict):
        extra = s.pop("custom", {}) if isinstance(s.get("custom"), dict) else {}
    else:
        s.pop("custom", None)
    for key, category in list(extra.items()):
        if isinstance(category, list):
            extra[key] = clean_list(category)
        elif isinstance(category, dict) and "lista" in category:
            category["lista"] = clean_list(category.get("lista"))
            if "maximo" in category:
                category["maximo"] = max(0, to_int(category.get("maximo"), 3))
    s["extra"] = extra
    return apply_rules(s)
