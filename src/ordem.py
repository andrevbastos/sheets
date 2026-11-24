"""Ficha de Ordem Paranormal: perícias, regras automáticas e normalização.

As regras vêm do livro básico (páginas citadas em cada função). `apply_rules(sheet)` grava os
valores derivados na própria ficha, então o JSON salvo e o que a rede envia já vêm calculados.
"""
import copy
import re
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

# Origens (Tabela 1.1, p. 29; descrições p. 26-31): duas perícias treinadas + um poder.
# "resumo" é um resumo curto do poder (não é o texto do livro).
ORIGENS = {
    "academico": ("Acadêmico", ("ciencias", "investigacao"), "Saber é Poder", "2 PE: +5 num teste de Intelecto."),
    "agente de saude": ("Agente de Saúde", ("intuicao", "medicina"), "Técnica Medicinal",
                        "Soma o Intelecto nos PV que cura."),
    "amnesico": ("Amnésico", (), "Vislumbres do Passado",
                 "Perícias à escolha do mestre. 1x por sessão, teste de INT (DT 10) para reconhecer algo do passado."),
    "artista": ("Artista", ("artes", "enganacao"), "Magnum Opus",
                "1x por missão, alguém o reconhece: +5 em testes de Presença contra essa pessoa."),
    "atleta": ("Atleta", ("acrobacia", "atletismo"), "110%",
               "2 PE: +5 num teste de perícia de FOR ou AGI (exceto Luta e Pontaria)."),
    "chef": ("Chef", ("fortitude", "profissao"), "Ingrediente Secreto",
             "No interlúdio, o grupo que comer recebe o benefício de dois pratos."),
    "criminoso": ("Criminoso", ("crime", "furtividade"), "O Crime Compensa",
                  "Um item achado na missão vem na próxima sem contar no limite."),
    "cultista arrependido": ("Cultista Arrependido", ("ocultismo", "religiao"), "Traços do Outro Lado",
                             "Um poder paranormal à escolha; Sanidade inicial pela metade."),
    "desgarrado": ("Desgarrado", ("fortitude", "sobrevivencia"), "Calejado", "+1 PV por nível de NEX."),
    "engenheiro": ("Engenheiro", ("profissao", "tecnologia"), "Ferramenta Favorita",
                   "Um item (não arma) conta uma categoria abaixo."),
    "executivo": ("Executivo", ("diplomacia", "profissao"), "Processo Otimizado",
                  "2 PE: +5 em teste estendido ou ao revisar documentos."),
    "investigador": ("Investigador", ("investigacao", "percepcao"), "Faro para Pistas",
                     "1x por cena, 1 PE: +5 para procurar pistas."),
    "lutador": ("Lutador", ("luta", "reflexos"), "Mão Pesada", "+2 no dano corpo a corpo."),
    "magnata": ("Magnata", ("diplomacia", "pilotagem"), "Patrocinador da Ordem", "Limite de crédito um acima."),
    "mercenario": ("Mercenário", ("iniciativa", "intimidacao"), "Posição de Combate",
                   "1º turno da cena de ação, 2 PE: ação de movimento extra."),
    "militar": ("Militar", ("pontaria", "tatica"), "Para Bellum", "+2 no dano com armas de fogo."),
    "operario": ("Operário", ("fortitude", "profissao"), "Ferramenta de Trabalho",
                 "Uma arma-ferramenta: proficiência e +1 em ataque, dano e margem de ameaça."),
    "policial": ("Policial", ("percepcao", "pontaria"), "Patrulha", "+2 na Defesa."),
    "religioso": ("Religioso", ("religiao", "vontade"), "Acalentar",
                  "+5 em Religião para acalmar; quem é acalmado recupera 1d6+PRE de SAN."),
    "servidor publico": ("Servidor Público", ("intuicao", "vontade"), "Espírito Cívico",
                         "1 PE: +2 no bônus quando ajuda alguém."),
    "teorico da conspiracao": ("Teórico da Conspiração", ("investigacao", "ocultismo"), "Eu Já Sabia",
                               "Resistência a dano mental igual ao Intelecto."),
    "t.i.": ("T.I.", ("investigacao", "tecnologia"), "Motor de Busca",
             "Com internet, 2 PE: troca um teste de perícia por Tecnologia."),
    "trabalhador rural": ("Trabalhador Rural", ("adestramento", "sobrevivencia"), "Desbravador",
                          "2 PE: +5 em Adestramento ou Sobrevivência; ignora terreno difícil."),
    "trambiqueiro": ("Trambiqueiro", ("crime", "enganacao"), "Impostor",
                     "1x por cena, 2 PE: troca um teste de perícia por Enganação."),
    "universitario": ("Universitário", ("atualidades", "investigacao"), "Dedicação",
                      "+1 PE e +1 a cada NEX ímpar (15%, 25%…); +1 no limite de PE por rodada."),
    "vitima": ("Vítima", ("reflexos", "vontade"), "Cicatrizes Psicológicas", "+1 SAN por nível de NEX."),
}
ORIGEM_NOMES = [o[0] for o in ORIGENS.values()]
CREDITOS = ["Baixo", "Médio", "Alto", "Ilimitado"]

# Rituais (p. 119): elementos e custo em PE pelo círculo (Tabela 5.2)
ELEMENTOS = ["Conhecimento", "Energia", "Morte", "Sangue", "Medo"]
CUSTO_CIRCULO = {1: 1, 2: 3, 3: 6, 4: 10}

# Ameaças (p. 178-179): tamanho, testes que a ficha do livro mostra em destaque e tipos de ação
TIPO_AMEACA = "ameaca"
TAMANHOS = ["Minúsculo", "Pequeno", "Médio", "Grande", "Enorme", "Colossal"]
AMEACA_TESTES = [("percepcao", "Percepção", "pre"), ("iniciativa", "Iniciativa", "agi"),
                 ("fortitude", "Fortitude", "vig"), ("reflexos", "Reflexos", "agi"), ("vontade", "Vontade", "pre")]
TIPOS_ACAO = ["Padrão", "Movimento", "Completa", "Reação", "Livre"]

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


def _sem_genero(text) -> str:
    """'universitária' e 'teórica da conspiração' casam com a forma do livro (masculino)."""
    return " ".join(w[:-1] if len(w) > 3 and w[-1] in "ao" else w for w in _plain(text).split())


_ORIGENS_POR_NOME = {_sem_genero(key): key for key in ORIGENS}


def origin_key(sheet):
    """Chave da origem ("investigador"...) ou None se for outra/vazia."""
    return _ORIGENS_POR_NOME.get(_sem_genero(sheet.get("origem")))


def origem_info(sheet):
    """(nome, perícias, poder, resumo) da origem, ou None."""
    key = origin_key(sheet)
    return ORIGENS[key] if key else None


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
    """Limite de PE por turno (Tabela 1.2, p. 33): igual ao nível de exposição. É o que entra nas DTs."""
    return nex_nivel(sheet)


def pe_por_rodada(sheet) -> int:
    """Limite de PE por rodada mostrado na ficha. Universitário (Dedicação, p. 31) tem +1, sem mudar as DTs."""
    return limite_pe(sheet) + (1 if origin_key(sheet) == "universitario" else 0)


def bonus_de_origem(sheet, key) -> int:
    """PV/PE/SAN extras dados pelo poder da origem (p. 28 e 31)."""
    origem, niveis = origin_key(sheet), nex_nivel(sheet)
    if key == "pv" and origem == "desgarrado":       # Calejado: +1 PV por 5% de NEX
        return niveis
    if key == "san" and origem == "vitima":          # Cicatrizes Psicológicas: +1 SAN por 5% de NEX
        return niveis
    if key == "pe" and origem == "universitario":    # Dedicação: +1 PE, +1 a cada NEX ímpar (15%, 25%…)
        return 1 + sum(1 for level in range(15, 100, 10) if level <= sheet.get("nex", 5))
    return 0


def recurso_calculado(sheet, key):
    """Máximo de PV/PE/SAN pela classe, NEX e atributo (p. 33-43) e pela origem, ou None se a classe é outra."""
    cls = class_key(sheet)
    if cls is None:
        return None
    inicial, por_nex, attr = CLASSES[cls][key]
    if key == "san" and origin_key(sheet) == "cultista arrependido":
        inicial //= 2  # Traços do Outro Lado: começa com metade da Sanidade da classe
    bonus_attr = sheet["atributos"].get(attr, 0) if attr else 0
    niveis_extras = nex_nivel(sheet) - 1
    casca_grossa = nex_nivel(sheet) if key == "pv" and tem_habilidade(sheet, "tropa", 10) else 0  # p. 27
    return (inicial + bonus_attr + niveis_extras * (por_nex + bonus_attr) + bonus_de_origem(sheet, key)
            + casca_grossa)


def dt_rituais(sheet) -> int:
    """DT para resistir aos rituais (p. 131): 10 + limite de PE + Presença."""
    return 10 + limite_pe(sheet) + sheet["atributos"].get("pre", 0)


def carga_maxima(sheet) -> int:
    """Espaços de itens (p. 63): 5 por ponto de Força; com Força 0, apenas 2."""
    forca = sheet["atributos"].get("for", 0)
    if tem_habilidade(sheet, "tecnico", 10):  # Inventário Otimizado (p. 31): soma o Intelecto à Força
        forca += sheet["atributos"].get("int", 0)
    return 5 * forca if forca > 0 else 2


def carga_absoluta(sheet) -> int:
    """Ninguém carrega mais que o dobro da carga máxima (p. 63)."""
    return 2 * sheet.get("inventario", {}).get("carga_max", carga_maxima(sheet))


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
    credito = atual[2]
    if origin_key(sheet) == "magnata":  # Patrocinador da Ordem: crédito um acima (p. 30)
        credito = CREDITOS[min(CREDITOS.index(credito) + 1, len(CREDITOS) - 1)]
    return atual[1], credito, dict(zip(CATEGORIAS, atual[3]))


def itens_por_categoria(sheet) -> dict:
    counts = {c: 0 for c in CATEGORIAS}
    for item in sheet.get("inventario", {}).get("itens", []):
        cat = str(item.get("categoria", "")).strip().upper()
        if cat in counts:
            counts[cat] += 1
    return counts


def defesa_origem(sheet) -> int:
    """Policial (Patrulha, p. 30): +2 na Defesa."""
    return 2 if origin_key(sheet) == "policial" else 0


def defesa_total(sheet) -> int:
    """Defesa (p. 46): 10 + AGI + equipamento + outros (+ origem); sobrecarregado sofre −5 (p. 63)."""
    d = sheet.get("defesa", {})
    total = (10 + sheet.get("atributos", {}).get("agi", 0) + d.get("equipamento", 0) + d.get("outros", 0)
             + defesa_origem(sheet) - penalidade_defesa(sheet)[0])  # condições (p. 310-311)
    if tem_habilidade(sheet, "tropa", 99) and machucado_agente(sheet):  # Inquebrável (p. 27)
        total += 5
    return total - 5 if sobrecarregado(sheet) else total


def bonus_pericia(sheet, key) -> int:
    """Grau de treino + outros; perícias de carga sofrem −5 quando sobrecarregado (p. 63)."""
    p = sheet.get("pericias", {}).get(key, {})
    total = p.get("treino", 0) + p.get("outros", 0)
    if key == "iniciativa" and tem_habilidade(sheet, "operacoes", 10):  # Iniciativa Aprimorada (p. 27)
        total += 5
    if key in PERICIAS_CARGA and sobrecarregado(sheet):
        total -= 5
    return total


def dados(sheet, attr) -> str:
    """Dados do teste (p. 24): 1d20 por ponto do atributo; atributo 0 rola 2d20 e fica com o pior."""
    valor = sheet.get("atributos", {}).get(attr, 0)
    return f"{valor}d20" if valor > 0 else "2d20↓"


# ------------------------------------------------------------------ rolagens
_TESTE_RE = re.compile(r"(?<![\wÀ-ÿ])(\d*)d20(↓)?(?![\wÀ-ÿ])\s*(?:([+\-−])\s*(\d+))?", re.I)
# Notação do livro (2O+10, O+5, O = d20). O app escreve 3d20+10; esta só serve para converter fichas antigas.
# Só casa com número antes do O ("2O") ou bônus depois ("O+5"), para não pegar o artigo "O" num texto.
_LIVRO_RE = re.compile(r"(?<![\wÀ-ÿ])(?:(\d+)O(?![\wÀ-ÿ])|O(?=\s*[+\-−]\s*\d))")
_BONUS_RE = re.compile(r"([+\-−])\s*(\d+)")
_PERICIA_POR_NOME = {_plain(nome): key for key, nome, *_ in PERICIAS}


def teste_request(n_dados: int, bonus: int, label="") -> dict:
    """Pedido de um teste (p. 24): n d20 e fica com o maior; com 0 dados, rola 2d20 e fica com o pior."""
    n_dados = max(0, min(n_dados, 11))
    if n_dados == 0:
        mode, extra = "desvantagem", 1
    elif n_dados == 1:
        mode, extra = "normal", 0
    else:
        mode, extra = "vantagem", n_dados - 1
    return {"sides": 20, "qty": 1, "mode": mode, "extra": extra, "bonus": bonus, "label": label}


def _fmt_dados(n_dados: int) -> str:
    return "2d20↓" if n_dados == 0 else f"{n_dados}d20"  # atributo 0: 2d20 e fica com o pior


def fmt_teste(n_dados: int, bonus: int) -> str:
    """'3d20+10', '1d20+5', '2d20↓' (atributo 0)."""
    return _fmt_dados(n_dados) + (f"+{bonus}" if bonus > 0 else f"-{-bonus}" if bonus < 0 else "")


def d20_notation(text) -> str:
    """Troca a notação do livro pelo dado inteiro: '2O+10' -> '2d20+10', 'O+5' -> '1d20+5', 'O' sozinho -> '1d20'."""
    text = str(text or "")
    if text.strip() == "O":
        return "1d20"
    return _LIVRO_RE.sub(lambda m: _fmt_dados(int(m.group(1) or 1)), text)


def _sinal(simbolo, numero) -> int:
    return int(numero) * (-1 if simbolo in ("-", "−") else 1)


def parse_teste(text):
    """'3d20+15', 'Luta 2d20+5', '2d20↓' -> (dados, bônus), ou None se o texto não traz os dados."""
    match = _TESTE_RE.search(d20_notation(text))
    if not match:
        return None
    n_dados = 0 if match.group(2) else int(match.group(1)) if match.group(1) else 1
    return n_dados, _sinal(match.group(3), match.group(4)) if match.group(4) else 0


def _pericia_no_texto(text):
    plain = _plain(text)
    for nome, key in _PERICIA_POR_NOME.items():
        if re.search(rf"(?<![a-z]){re.escape(nome)}(?![a-z])", plain):
            return key
    return None


def _pericia(key):
    return next(p for p in PERICIAS if p[0] == key)


def pericia_request(sheet, key, label=None, ataque=False) -> dict:
    """Teste de perícia do agente: dados do atributo + bônus (já com sobrecarga e condições)."""
    _, nome, attr, *_ = _pericia(key)
    return _com_condicoes(sheet, sheet["atributos"].get(attr, 0), bonus_pericia(sheet, key), label or nome,
                          key, ataque)


def ataque_request(sheet, text, label=""):
    """Teste de ataque escrito à mão: '3d20+10', 'Luta', 'Luta +2' ou '+5'. None se não der para entender."""
    text = str(text or "")
    parsed = parse_teste(text)
    key = _pericia_no_texto(text)
    if parsed:
        return _com_condicoes(sheet, *parsed, label, key, ataque=True)
    if is_ameaca(sheet):
        return ameaca_pericia_request(sheet, key, label, ataque=True) if key else None
    extra = sum(_sinal(m.group(1), m.group(2)) for m in _BONUS_RE.finditer(text))
    if key:
        req = pericia_request(sheet, key, label, ataque=True)
        req["bonus"] += extra
        return req
    if re.fullmatch(r"\s*[+\-−]\s*\d+\s*", text):
        return _com_condicoes(sheet, 1, extra, label, ataque=True)
    return None


def dano_request(text, label=""):
    """Rolagem de dano ('2d6+4 corte'). None se o texto não tem dados."""
    from src import dice  # tardio: evita importar a rolagem só para normalizar fichas
    req = dice.parse_dice(text)
    return {**req, "label": label} if req else None


def iniciativa_request(sheet, label=None) -> dict:
    label = label or f"{sheet.get('nome', '')} · Iniciativa"
    if is_ameaca(sheet):
        return ameaca_pericia_request(sheet, "iniciativa", label)
    return pericia_request(sheet, "iniciativa", label)


def custo_ritual(ritual) -> int:
    """PE do ritual pelo círculo (Tabela 5.2, p. 119), sem as formas discente/verdadeira."""
    return CUSTO_CIRCULO.get(ritual.get("circulo", 1), 1)


# ------------------------------------------------------------------ ameaças
def is_ameaca(sheet) -> bool:
    return isinstance(sheet, dict) and sheet.get("tipo") == TIPO_AMEACA


def machucado(sheet) -> int:
    """Limiar de 'machucado' das ameaças: metade dos PV (p. 178)."""
    return sheet["pv"]["max"] // 2


def pericias_ameaca(sheet):
    """Perícias extras escritas na ficha da ameaça ('Furtividade 2d20+13, Luta 3d20+10') -> [(nome, dados, bônus)]."""
    out = []
    for parte in re.split(r"[,;\n]", sheet.get("pericias", "")):
        parsed = parse_teste(parte)
        nome = _TESTE_RE.sub("", parte).strip(" .:")
        if parsed and nome:
            out.append((nome, *parsed))
    return out


def ameaca_pericia_request(sheet, key, label=None, ataque=False) -> dict:
    """Teste da ameaça: um dos cinco testes da ficha, uma perícia escrita ou, sem nada, só o atributo.
    As condições tiram dados como no agente."""
    _, nome, attr, *_ = _pericia(key)
    label = label or nome
    parsed = parse_teste(sheet.get("testes", {}).get(key, ""))
    if not parsed:
        parsed = next(((n_dados, bonus) for outro, n_dados, bonus in pericias_ameaca(sheet)
                       if _pericia_no_texto(outro) == key), (sheet["atributos"].get(attr, 0), 0))
    return _com_condicoes(sheet, *parsed, label, key, ataque)


def normalize_ameaca(sheet: dict, to_int, clean_list) -> dict:
    """Ficha de ameaça (p. 178-179), só do mestre. Os números já vêm prontos, como no livro."""
    s = copy.deepcopy(sheet)
    s["sistema"], s["tipo"] = SYSTEM, TIPO_AMEACA
    s["nome"] = str(s.get("nome") or "Sem Nome")
    cor = str(s.get("cor") or "").strip()
    s["cor"] = cor if cor.startswith("#") and len(cor) in (4, 7) else "#7a1f1f"
    for key in ("vd", "descritores", "deslocamento"):
        s[key] = str(s.get(key) or "")
    n = d20_notation  # fichas antigas com a notação do livro (2O+10) passam a mostrar 2d20+10
    for key in ("sentidos", "resistencias", "vulnerabilidades", "pericias"):
        s[key] = n(s.get(key))
    if not s["deslocamento"]:
        s["deslocamento"] = "9m"
    s["tamanho"] = next((t for t in TAMANHOS if _plain(t) == _plain(s.get("tamanho"))), "Médio")
    pres = s.get("presenca") if isinstance(s.get("presenca"), dict) else {}
    s["presenca"] = {"dt": max(0, to_int(pres.get("dt"), 0)), "dano": str(pres.get("dano") or ""),
                     "imune": str(pres.get("imune") or "")}
    attrs = s.get("atributos") if isinstance(s.get("atributos"), dict) else {}
    s["atributos"] = {key: max(0, to_int(attrs.get(key), 1)) for key, _, _ in ATRIBUTOS}
    testes = s.get("testes") if isinstance(s.get("testes"), dict) else {}
    s["testes"] = {key: n(testes.get(key)) or fmt_teste(s["atributos"][attr], 0) for key, _, attr in AMEACA_TESTES}
    s["defesa"] = to_int(s.get("defesa"), 10)
    pv = s.get("pv") if isinstance(s.get("pv"), dict) else {}
    maximo = max(0, to_int(pv.get("max"), 0))
    s["pv"] = {"max": maximo, "atual": max(0, to_int(pv.get("atual"), maximo))}
    s["habilidades"] = [{"nome": str(h.get("nome") or ""), "descricao": n(h.get("descricao"))}
                        for h in clean_list(s.get("habilidades")) if isinstance(h, dict)]
    s["acoes"] = [
        {"tipo": a.get("tipo") if a.get("tipo") in TIPOS_ACAO else "Padrão",
         "nome": str(a.get("nome") or ""), "teste": n(a.get("teste")), "dano": str(a.get("dano") or ""),
         "descricao": n(a.get("descricao"))}
        for a in clean_list(s.get("acoes")) if isinstance(a, dict)
    ]
    desc = s.get("descricao") if isinstance(s.get("descricao"), dict) else {}
    s["descricao"] = {key: n(desc.get(key)) for key, _ in DESCRICAO}
    s["condicoes"] = _condicoes(s.get("condicoes"))
    return apply_rules(s)


def _aplicar_pericias_da_origem(sheet):
    """As duas perícias da origem ficam no mínimo Treinado (p. 26).

    `origem_pericias` guarda o que a origem atual deu; ao trocar de origem, as perícias da antiga
    que ainda estão só em Treinado voltam a Destreinado (as que subiram para Veterano/Expert ficam).
    """
    info = origem_info(sheet)
    novas = list(info[1]) if info else []
    for key in sheet.get("origem_pericias", []):
        p = sheet["pericias"].get(key)
        if key not in novas and p and p["treino"] == 5:
            p["treino"] = 0
    for key in novas:
        sheet["pericias"][key]["treino"] = max(sheet["pericias"][key]["treino"], 5)
    if origin_key(sheet) == "chef" and not sheet.get("profissao_nome"):
        sheet["profissao_nome"] = "cozinheiro"
    sheet["origem_pericias"] = novas


def apply_rules(sheet: dict) -> dict:
    """Grava na ficha (no lugar) tudo o que as regras definem. Devolve a própria ficha."""
    if is_ameaca(sheet):
        sheet["pv"]["atual"] = max(0, min(sheet["pv"]["atual"], sheet["pv"]["max"]))
        return sheet
    sheet["nex"] = nex_valido(sheet.get("nex", 5))
    if sheet.get("trilha") not in {key for key, *_ in trilhas_da_classe(sheet)}:
        sheet["trilha"] = ""  # trocou de classe: a trilha da outra não vale
    sheet["pe_rodada"] = pe_por_rodada(sheet)
    sheet["dt_rituais"] = dt_rituais(sheet)
    _aplicar_pericias_da_origem(sheet)

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
    _aplicar_estados(sheet)
    return sheet


def normalize(sheet: dict, to_int, clean_list) -> dict:
    if is_ameaca(sheet):
        return normalize_ameaca(sheet, to_int, clean_list)
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
    anteriores = s.get("origem_pericias") if isinstance(s.get("origem_pericias"), list) else []
    s["origem_pericias"] = [k for k in anteriores if k in s["pericias"]]

    s["ataques"] = [
        {**{k: str(a.get(k) or "") for k in ("nome", "dano", "especial")}, "teste": d20_notation(a.get("teste"))}
        for a in clean_list(s.get("ataques")) if isinstance(a, dict)
    ]
    s["habilidades"] = [
        {"nome": str(h.get("nome") or ""),
         # a tela já mostra "PE" e "Pág.", então o valor guardado é só o número
         "custo": re.sub(r"\s*PE\s*$", "", str(h.get("custo") or ""), flags=re.I),
         "pagina": re.sub(r"^\s*p[áa]g\.?\s*", "", str(h.get("pagina") or ""), flags=re.I),
         "descricao": str(h.get("descricao") or "")}
        for h in clean_list(s.get("habilidades")) if isinstance(h, dict)
    ]

    s["rituais"] = [
        {"nome": str(r.get("nome") or ""),
         "elemento": next((e for e in ELEMENTOS if _plain(e) == _plain(r.get("elemento"))), ""),
         "circulo": max(1, min(to_int(r.get("circulo"), 1), 4)),
         **{k: str(r.get(k) or "") for k in ("execucao", "alcance", "alvo", "duracao", "resistencia", "dano")},
         "pagina": re.sub(r"^\s*p[áa]g\.?\s*", "", str(r.get("pagina") or ""), flags=re.I),
         "descricao": str(r.get("descricao") or "")}
        for r in clean_list(s.get("rituais")) if isinstance(r, dict)
    ]

    inv = s.get("inventario") if isinstance(s.get("inventario"), dict) else {}
    s["inventario"] = {
        "pontos_prestigio": max(0, to_int(inv.get("pontos_prestigio"), 0)),
        "itens": [
            {"nome": str(i.get("nome") or ""), "categoria": str(i.get("categoria") or ""),
             "espacos": max(0, to_int(i.get("espacos"), 0)), "descricao": str(i.get("descricao") or "")}
            for i in clean_list(inv.get("itens")) if isinstance(i, dict)
        ],
    }

    desc = s.get("descricao") if isinstance(s.get("descricao"), dict) else {}
    s["descricao"] = {key: str(desc.get(key) or "") for key, _ in DESCRICAO}
    e = s.get("estados") if isinstance(s.get("estados"), dict) else {}
    s["estados"] = {key: bool(e.get(key, False)) for key in ("morrendo", "enlouquecendo", "pv_zerado", "san_zerada")}
    for key in ("turnos_morrendo", "turnos_enlouquecendo"):
        s["estados"][key] = to_int(e.get(key), 0)
    s["condicoes"] = _condicoes(s.get("condicoes"))
    trilha = _plain(s.get("trilha"))
    s["trilha"] = next((k for k, (_, nome, *_) in TRILHA.items() if trilha in (k, _plain(nome))), "")
    s["afinidade"] = next((e for e in AFINIDADES if _plain(e) == _plain(s.get("afinidade"))), "")
    return apply_rules(s)


# ------------------------------------------------------------------ estados do agente (p. 88 e 111; errata p. 310)
TURNOS_FATAIS = 3  # iniciar três turnos morrendo/enlouquecendo na mesma cena = morte/insanidade


def machucado_agente(sheet) -> bool:
    """Metade ou menos dos PV totais (p. 88). Não dá penalidade, mas é pré-requisito de habilidades."""
    pv = sheet["pv"]
    return pv["max"] > 0 and pv["atual"] * 2 <= pv["max"]


def inconsciente(sheet) -> bool:
    """Com 0 PV; acaba com qualquer cura de pelo menos 1 PV (p. 88)."""
    return sheet["pv"]["max"] > 0 and sheet["pv"]["atual"] == 0


def _aplicar_estados(sheet):
    """Chegar a 0 PV liga "morrendo"; curar PV não desliga (só Medicina DT 20 ou efeitos, p. 88).
    Chegar a 0 SAN liga "enlouquecendo"; qualquer cura de SAN desliga (errata da p. 310)."""
    e = sheet["estados"]
    pv0 = inconsciente(sheet)
    if pv0 and not e["pv_zerado"]:
        e["morrendo"] = True
    e["pv_zerado"] = pv0
    san = sheet["san"]
    san0 = san["max"] > 0 and san["atual"] == 0
    if san0 and not e["san_zerada"]:
        e["enlouquecendo"] = True
    elif san["atual"] > 0:
        e["enlouquecendo"] = False
    e["san_zerada"] = san0
    for key in ("turnos_morrendo", "turnos_enlouquecendo"):
        e[key] = max(0, min(e[key], TURNOS_FATAIS))


def estabilizar(sheet):
    """Primeiros socorros (Medicina DT 20, p. 56): perde inconsciente e morrendo e fica com 1 PV.
    Os turnos contados continuam valendo até o fim da cena."""
    sheet["estados"]["morrendo"] = False
    sheet["pv"]["atual"] = max(1, sheet["pv"]["atual"])


def acalmar(sheet):
    """Acalmar (Diplomacia ou Religião DT 20, p. 54 e 58): o personagem fica com Sanidade 1."""
    sheet["san"]["atual"] = max(1, sheet["san"]["atual"])
    sheet["estados"]["enlouquecendo"] = False


def nova_cena(sheet):
    """Os turnos morrendo/enlouquecendo contam por cena: uma cena nova zera a contagem."""
    sheet["estados"]["turnos_morrendo"] = sheet["estados"]["turnos_enlouquecendo"] = 0


def morto(sheet) -> bool:
    return sheet["estados"]["turnos_morrendo"] >= TURNOS_FATAIS


def insano(sheet) -> bool:
    return sheet["estados"]["turnos_enlouquecendo"] >= TURNOS_FATAIS


def estados_texto(sheet):
    """Estados para mostrar em resumo (barra lateral): [(texto, grave)]."""
    if is_ameaca(sheet):
        pv = sheet["pv"]
        if pv["max"] and pv["atual"] == 0:
            return [("DERROTADA", True)]
        return [("MACHUCADA", False)] if pv["max"] and pv["atual"] <= machucado(sheet) else []
    e, out = sheet["estados"], []
    if morto(sheet):
        out.append(("MORTO", True))
    elif e["morrendo"]:
        out.append((f"MORRENDO {e['turnos_morrendo']}/{TURNOS_FATAIS}", True))
    elif inconsciente(sheet):
        out.append(("INCONSCIENTE", True))
    elif machucado_agente(sheet):
        out.append(("MACHUCADO", False))
    if insano(sheet):
        out.append(("INSANO", True))
    elif e["enlouquecendo"]:
        out.append((f"ENLOUQUECENDO {e['turnos_enlouquecendo']}/{TURNOS_FATAIS}", True))
    return out


# ------------------------------------------------------------------ condições (p. 310-311, com a errata)
# (chave, nome, resumo, piora para). Resumos curtos escritos para a ficha; o texto completo está no livro.
# "piora para": receber a mesma condição de novo vira a seguinte (abalado duas vezes = apavorado).
# Machucado, morrendo e enlouquecendo não estão aqui: a ficha calcula sozinha (ver estados acima).
# Salvo indicação contrária, condições acabam no fim da cena.
CONDICOES = [
    ("abalado", "Abalado", "−1d20 em testes. Medo.", "apavorado"),
    ("agarrado", "Agarrado", "Desprevenido e imóvel; −1d20 em ataques, só armas leves. Tiro de fora pode "
                             "acertar o alvo errado (50%). Paralisia.", None),
    ("alquebrado", "Alquebrado", "Habilidades e rituais custam +1 PE. Mental.", None),
    ("apavorado", "Apavorado", "−2d20 em perícias; foge da fonte do medo ou não pode se aproximar dela. Medo.",
     None),
    ("asfixiado", "Asfixiado", "Sem respirar: aguenta rodadas = Vigor; depois Fortitude DT 5 (+5 por teste) "
                               "a cada rodada; falhou, inconsciente e −1d6 PV por rodada.", None),
    ("atordoado", "Atordoado", "Desprevenido e sem ações. Mental.", None),
    ("caido", "Caído", "−2d20 em ataques corpo a corpo, deslocamento 1,5 m; Defesa −5 contra corpo a corpo e "
                       "+5 contra ataques à distância.", None),
    ("cego", "Cego", "Desprevenido e lento; sem Percepção para ver; −2d20 em perícias de AGI e FOR; os alvos "
                     "têm camuflagem total. Sentidos.", None),
    ("confuso", "Confuso", "1d6 no início do turno: 1 anda ao acaso (1d8), 2-3 não age, 4-5 ataca o mais "
                           "próximo, 6 a condição acaba. Mental.", None),
    ("debilitado", "Debilitado", "−2d20 em testes de AGI, FOR e VIG.", "inconsciente"),
    ("desprevenido", "Desprevenido", "−5 na Defesa e −1d20 em Reflexos.", None),
    ("doente", "Doente", "Efeito da doença.", None),
    ("em_chamas", "Em Chamas", "1d6 de fogo no início do turno; ação padrão (ou água) apaga.", None),
    ("enjoado", "Enjoado", "Só uma ação padrão ou de movimento por rodada.", None),
    ("enredado", "Enredado", "Lento, vulnerável e −1d20 em ataques. Paralisia.", None),
    ("envenenado", "Envenenado", "Efeito do veneno (outra condição ou dano por rodada, que se acumula).", None),
    ("esmorecido", "Esmorecido", "−2d20 em testes de INT e PRE. Mental.", None),
    ("exausto", "Exausto", "Debilitado, lento e vulnerável. Fadiga.", "inconsciente"),
    ("fascinado", "Fascinado", "−2d20 em Percepção, só observa o que o fascinou; ação hostil encerra. Mental.",
     None),
    ("fatigado", "Fatigado", "Fraco e vulnerável. Fadiga.", "exausto"),
    ("fraco", "Fraco", "−1d20 em testes de AGI, FOR e VIG.", "debilitado"),
    ("frustrado", "Frustrado", "−1d20 em testes de INT e PRE. Mental.", "esmorecido"),
    ("imovel", "Imóvel", "Deslocamento 0 m. Paralisia.", None),
    ("inconsciente", "Inconsciente", "Indefeso e sem ações nem reações; acordar alguém gasta ação padrão.", None),
    ("indefeso", "Indefeso", "Desprevenido, −10 na Defesa, falha em Reflexos, sofre golpe de misericórdia.",
     None),
    ("lento", "Lento", "Deslocamento pela metade; não corre nem faz investida. Paralisia.", None),
    ("ofuscado", "Ofuscado", "−1d20 em ataques e Percepção. Sentidos.", None),
    ("paralisado", "Paralisado", "Imóvel e indefeso; só ações puramente mentais. Paralisia.", None),
    ("pasmo", "Pasmo", "Sem ações. Mental.", None),
    ("perturbado", "Perturbado", "Na primeira vez na cena, recebe um efeito de insanidade (p. 111).", None),
    ("petrificado", "Petrificado", "Inconsciente, com resistência a dano 10.", None),
    ("sangrando", "Sangrando", "Vigor DT 20 no início do turno: passou, para; falhou, −1d6 PV. Medicina DT 20 "
                               "(ação completa) estabiliza.", None),
    ("surdo", "Surdo", "Sem Percepção para ouvir, −2d20 em Iniciativa, condição ruim para rituais. Sentidos.",
     None),
    ("surpreendido", "Surpreendido", "Desprevenido e sem ações.", None),
    ("vulneravel", "Vulnerável", "−2 na Defesa.", None),
]
CONDICAO = {key: (nome, resumo, piora) for key, nome, resumo, piora in CONDICOES}


def adicionar_condicao(sheet, key):
    """Põe a condição na ficha. Se ela (ou uma pior da mesma linha) já está, piora um passo:
    fatigado -> exausto -> inconsciente, fraco -> debilitado -> inconsciente, abalado -> apavorado..."""
    cadeia = [key]
    while CONDICAO[cadeia[-1]][2]:
        cadeia.append(CONDICAO[cadeia[-1]][2])
    atuais = sheet["condicoes"]
    presentes = [i for i, c in enumerate(cadeia) if c in atuais]
    if not presentes:
        atuais.append(key)
        return key
    i = presentes[-1]
    if i + 1 < len(cadeia):
        atuais[atuais.index(cadeia[i])] = cadeia[i + 1]
    for c in cadeia[:i]:  # um passo anterior que tenha sobrado fica coberto pelo pior
        if c in atuais:
            atuais.remove(c)
    return cadeia[min(i + 1, len(cadeia) - 1)]


def remover_condicao(sheet, key):
    if key in sheet["condicoes"]:
        sheet["condicoes"].remove(key)


def _condicoes(valor):
    """Lista de chaves válidas, sem repetir (aceita nomes com acento e maiúsculas)."""
    por_nome = {_plain(nome): key for key, nome, *_ in CONDICOES}
    out = []
    for item in valor if isinstance(valor, list) else []:
        key = item if item in CONDICAO else por_nome.get(_plain(item))
        if key and key not in out:
            out.append(key)
    return out


def condicoes_texto(sheet) -> str:
    return ", ".join(CONDICAO[key][0].lower() for key in sheet.get("condicoes", []) if key in CONDICAO)


# ------------------------------------------------------------------ penalidades das condições (p. 310-311)
# Cada "–O" tira 1d20 do teste (p. 76); com 0 dados rola 2d20 e fica com o pior (p. 24). O livro não diz o
# que acontece abaixo de 0, então para em 2d20↓. Condições que "incluem" outras (exausto = debilitado, lento
# e vulnerável) contam as incluídas. Numa mesma linha vale só a pior (fraco/debilitado, abalado/apavorado,
# frustrado/esmorecido); linhas diferentes somam. Caído na Defesa depende do ataque (±5): fica só no aviso.
IMPLICA = {
    "agarrado": ("desprevenido", "imovel"), "atordoado": ("desprevenido",), "cego": ("desprevenido", "lento"),
    "exausto": ("debilitado", "lento", "vulneravel"), "fatigado": ("fraco", "vulneravel"),
    "enredado": ("lento", "vulneravel"), "paralisado": ("imovel", "indefeso"), "inconsciente": ("indefeso",),
    "petrificado": ("inconsciente",), "surpreendido": ("desprevenido",), "indefeso": ("desprevenido",),
}
_FISICOS, _MENTAIS = ("agi", "for", "vig"), ("int", "pre")
# (condição, d20 a menos, linha, vale para (perícia, atributo, é ataque))
PENALIDADES_DADOS = [
    ("abalado", 1, "medo", lambda k, a, atk: True),
    ("apavorado", 2, "medo", lambda k, a, atk: True),  # "em testes de perícia": todo teste da ficha é de perícia
    ("fraco", 1, "fisico", lambda k, a, atk: a in _FISICOS),
    ("debilitado", 2, "fisico", lambda k, a, atk: a in _FISICOS),
    ("frustrado", 1, "mental", lambda k, a, atk: a in _MENTAIS),
    ("esmorecido", 2, "mental", lambda k, a, atk: a in _MENTAIS),
    ("cego", 2, "cego", lambda k, a, atk: a in ("agi", "for")),
    ("fascinado", 2, "fascinado", lambda k, a, atk: k == "percepcao"),
    ("ofuscado", 1, "ofuscado", lambda k, a, atk: atk or k == "percepcao"),
    ("surdo", 2, "surdo", lambda k, a, atk: k == "iniciativa"),
    ("desprevenido", 1, "desprevenido", lambda k, a, atk: k == "reflexos"),
    ("agarrado", 1, "agarrado", lambda k, a, atk: atk),
    ("enredado", 1, "enredado", lambda k, a, atk: atk),
    ("caido", 2, "caido", lambda k, a, atk: atk and k == "luta"),  # só corpo a corpo
]


def condicoes_efetivas(sheet) -> set:
    """Condições marcadas + as que elas incluem (+ inconsciente com 0 PV, no agente)."""
    pendentes = list(sheet.get("condicoes", []))
    if (not is_ameaca(sheet) and "estados" in sheet and inconsciente(sheet)
            and not tem_habilidade(sheet, "tropa", 99)):  # Inquebrável: morrendo não fica indefeso
        pendentes.append("inconsciente")
    out = set()
    while pendentes:
        key = pendentes.pop()
        if key not in out:
            out.add(key)
            pendentes.extend(IMPLICA.get(key, ()))
    return out


def penalidade_dados(sheet, key=None, ataque=False):
    """(d20 a menos, [nomes das condições]) num teste da perícia `key` (ou ataque)."""
    efetivas = condicoes_efetivas(sheet)
    if not efetivas:
        return 0, []
    attr = _pericia(key)[2] if key else None
    pior = {}
    for cond, n, linha, vale in PENALIDADES_DADOS:
        if cond in efetivas and vale(key, attr, ataque) and n > pior.get(linha, (0, ""))[0]:
            pior[linha] = (n, cond)
    nomes = [CONDICAO[c][0].lower() for _, c in pior.values()]
    return sum(n for n, _ in pior.values()), nomes


def penalidade_defesa(sheet):
    """(pontos a menos na Defesa, [nomes]): desprevenido −5 (indefeso −10 no lugar), vulnerável −2."""
    efetivas = condicoes_efetivas(sheet)
    total, nomes = 0, []
    if "indefeso" in efetivas:
        total, nomes = 10, ["indefeso"]
    elif "desprevenido" in efetivas:
        total, nomes = 5, ["desprevenido"]
    if "vulneravel" in efetivas:
        total, nomes = total + 2, nomes + ["vulnerável"]
    return total, nomes


def _com_condicoes(sheet, n_dados, bonus, label, key=None, ataque=False):
    """Pedido do teste já sem os d20 que as condições tiram; o motivo vai no nome da rolagem."""
    menos, nomes = penalidade_dados(sheet, key, ataque)
    if menos:
        n_dados = max(0, n_dados - menos)
        label = f"{label} (−{menos}d20: {', '.join(nomes)})" if label else f"−{menos}d20: {', '.join(nomes)}"
    return teste_request(n_dados, bonus, label)


def dados_pericia(sheet, key) -> str:
    """Dados do teste da perícia já com as condições ('3d20', '2d20↓')."""
    attr = _pericia(key)[2]
    return _fmt_dados(max(0, sheet["atributos"].get(attr, 0) - penalidade_dados(sheet, key)[0]))


def defesa_ameaca(sheet) -> int:
    return sheet.get("defesa", 0) - penalidade_defesa(sheet)[0]


# ------------------------------------------------------------------ trilhas e afinidade (p. 26-35 e 114)
# A trilha é escolhida em NEX 10% e dá uma habilidade em NEX 10%, 40%, 65% e 99%. Aqui ficam só os nomes e a
# página; as que mudam números da ficha estão em TRILHA_AUTOMATICA e entram nas contas sozinhas.
NEX_TRILHA = (10, 40, 65, 99)
TRILHAS = {
    "combatente": [
        ("aniquilador", "Aniquilador", 26, ("A Favorita", "Técnica Secreta", "Técnica Sublime", "Máquina de Matar")),
        ("comandante", "Comandante de Campo", 27,
         ("Inspirar Confiança", "Estrategista", "Brecha na Guarda", "Oficial Comandante")),
        ("guerreiro", "Guerreiro", 27, ("Técnica Letal", "Revidar", "Força Opressora", "Potência Máxima")),
        ("operacoes", "Operações Especiais", 27,
         ("Iniciativa Aprimorada", "Ataque Extra", "Surto de Adrenalina", "Sempre Alerta")),
        ("tropa", "Tropa de Choque", 27, ("Casca Grossa", "Cai Dentro", "Duro de Matar", "Inquebrável")),
    ],
    "especialista": [
        ("atirador", "Atirador de Elite", 30,
         ("Mira de Elite", "Disparo Letal", "Disparo Impactante", "Atirar para Matar")),
        ("infiltrador", "Infiltrador", 30, ("Ataque Furtivo", "Gatuno", "Assassinar", "Sombra Fugaz")),
        ("medico", "Médico de Campo", 31, ("Paramédico", "Equipe de Trauma", "Resgate", "Reanimação")),
        ("negociador", "Negociador", 31,
         ("Eloquência", "Discurso Motivador", "Eu Conheço um Cara", "Truque de Mestre")),
        ("tecnico", "Técnico", 31, ("Inventário Otimizado", "Remendão", "Improvisar", "Preparado para Tudo")),
    ],
    "ocultista": [
        ("conduite", "Conduíte", 34, ("Ampliar Ritual", "Acelerar Ritual", "Anular Ritual", "Canalizar o Medo")),
        ("flagelador", "Flagelador", 34, ("Poder do Flagelo", "Abraçar a Dor", "Absorver Agonia", "Medo Tangível")),
        ("graduado", "Graduado", 35,
         ("Saber Ampliado", "Grimório Ritualístico", "Rituais Eficientes", "Conhecendo o Medo")),
        ("intuitivo", "Intuitivo", 35, ("Mente Sã", "Presença Poderosa", "Inabalável", "Presença do Medo")),
        ("lamina", "Lâmina Paranormal", 35,
         ("Lâmina Maldita", "Gladiador Paranormal", "Conjuração Marcial", "Lâmina do Medo")),
    ],
}
TRILHA = {key: (cls, nome, pagina, habilidades)
          for cls, trilhas in TRILHAS.items() for key, nome, pagina, habilidades in trilhas}
# (trilha, NEX) -> o que a ficha já calcula
TRILHA_AUTOMATICA = {
    ("tropa", 10): "+1 PV por 5% de NEX",
    ("operacoes", 10): "+5 em Iniciativa",
    ("tecnico", 10): "carga com FOR + INT",
    ("tropa", 99): "+5 na Defesa machucado; morrendo não fica indefeso",
}
AFINIDADES = ["Conhecimento", "Energia", "Morte", "Sangue"]
NEX_AFINIDADE = 50


def tem_habilidade(sheet, trilha, nex) -> bool:
    return sheet.get("trilha") == trilha and sheet.get("nex", 5) >= nex


def habilidades_trilha(sheet):
    """[(NEX, nome, já tem, efeito automático ou "")] da trilha escolhida."""
    info = TRILHA.get(sheet.get("trilha"))
    if not info:
        return []
    return [(nex, nome, sheet.get("nex", 5) >= nex, TRILHA_AUTOMATICA.get((sheet["trilha"], nex), ""))
            for nex, nome in zip(NEX_TRILHA, info[3])]


def trilhas_da_classe(sheet):
    return TRILHAS.get(class_key(sheet), [])
