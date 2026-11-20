"""Dados da ficha de Ordem Paranormal: tabela de perícias e normalização.

Só o que a ficha oficial mostra; o único cálculo é o que está impresso nela
(Defesa = 10 + AGI + Equip. + Outros, e o bônus da perícia = Treino + Outros).
"""
import copy

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

RECURSOS = [("pv", "PV", "Pontos de Vida"), ("pe", "PE", "Pontos de Esforço"), ("san", "SAN", "Sanidade")]
CATEGORIAS = ["I", "II", "III", "IV"]
DESCRICAO = [("aparencia", "Aparência"), ("personalidade", "Personalidade"),
             ("historico", "Histórico"), ("objetivo", "Objetivo")]


def defesa_total(sheet) -> int:
    d = sheet.get("defesa", {})
    return 10 + sheet.get("atributos", {}).get("agi", 0) + d.get("equipamento", 0) + d.get("outros", 0)


def bonus_pericia(sheet, key) -> int:
    p = sheet.get("pericias", {}).get(key, {})
    return p.get("treino", 0) + p.get("outros", 0)


def espacos_usados(sheet) -> int:
    return sum(item.get("espacos", 0) for item in sheet.get("inventario", {}).get("itens", []))


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
    s["nex"] = max(0, min(to_int(s.get("nex"), 5), 100))
    s["pe_rodada"] = max(0, to_int(s.get("pe_rodada"), 1))

    attrs = s.get("atributos") if isinstance(s.get("atributos"), dict) else {}
    s["atributos"] = {key: max(0, to_int(attrs.get(key), 1)) for key, _, _ in ATRIBUTOS}

    for key, _, _ in RECURSOS:
        res = s.get(key) if isinstance(s.get(key), dict) else {}
        maximo = max(0, to_int(res.get("max"), 0))
        s[key] = {"max": maximo, "atual": max(0, min(to_int(res.get("atual"), maximo), maximo))}

    d = s.get("defesa") if isinstance(s.get("defesa"), dict) else {}
    s["defesa"] = {"equipamento": to_int(d.get("equipamento"), 0), "outros": to_int(d.get("outros"), 0)}

    per = s.get("pericias") if isinstance(s.get("pericias"), dict) else {}
    s["pericias"] = {}
    for key, *_ in PERICIAS:
        p = per.get(key) if isinstance(per.get(key), dict) else {}
        s["pericias"][key] = {"treino": to_int(p.get("treino"), 0), "outros": to_int(p.get("outros"), 0)}
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
    s["dt_rituais"] = to_int(s.get("dt_rituais"), 0)

    inv = s.get("inventario") if isinstance(s.get("inventario"), dict) else {}
    limites = inv.get("limite_itens") if isinstance(inv.get("limite_itens"), dict) else {}
    s["inventario"] = {
        "pontos_prestigio": to_int(inv.get("pontos_prestigio"), 0),
        "patente": str(inv.get("patente") or ""),
        "limite_itens": {c: max(0, to_int(limites.get(c), 0)) for c in CATEGORIAS},
        "limite_credito": str(inv.get("limite_credito") or ""),
        "carga_max": max(0, to_int(inv.get("carga_max"), 0)),
        "itens": [
            {"nome": str(i.get("nome") or ""), "categoria": str(i.get("categoria") or ""),
             "espacos": max(0, to_int(i.get("espacos"), 0))}
            for i in clean_list(inv.get("itens")) if isinstance(i, dict)
        ],
    }

    desc = s.get("descricao") if isinstance(s.get("descricao"), dict) else {}
    s["descricao"] = {key: str(desc.get(key) or "") for key, _ in DESCRICAO}
    return s
