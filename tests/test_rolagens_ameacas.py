"""Rolagens pela ficha, rituais e fichas de ameaça (Ordem Paranormal)."""
import json

import pytest

from src import dice, ordem
from src.net.server import DNDServer
from src.sheet_io import create_new_threat, load_sheet, normalize_sheet


def agente(**kw):
    base = {"sistema": "ordem", "classe": "Combatente", "nex": 5,
            "atributos": {"agi": 2, "for": 3, "int": 1, "pre": 1, "vig": 0}}
    base.update(kw)
    return normalize_sheet(base)


def ameaca(**kw):
    return normalize_sheet({"sistema": "ordem", "tipo": "ameaca", "nome": "Zumbi", **kw})


# ------------------------------------------------------------------ dados
@pytest.mark.parametrize("texto, esperado", [
    ("2d6+4 corte", (2, 6, 4)),
    ("1d3+1 impacto", (1, 3, 1)),
    ("2d6 + 4", (2, 6, 4)),
    ("1d8+1d6 Morte", (1, 8, 0)),   # só a primeira parte; o +1 do 1d6 não vira bônus
    ("d20", (1, 20, 0)),
])
def test_parse_dano(texto, esperado):
    req = dice.parse_dice(texto)
    assert (req["qty"], req["sides"], req["bonus"]) == esperado


@pytest.mark.parametrize("texto", ["", "alcance de 3m", "1d7", "Mordida"])
def test_parse_dano_sem_dado(texto):
    assert dice.parse_dice(texto) is None


def test_rotulo_aparece_no_historico_e_some_na_privada():
    req = dice.clean_request({"sides": 20, "label": "Sofia · Luta", "private": True})
    r = dice.roll(req, "Mestre")
    assert "Sofia · Luta" in dice.describe(r)
    assert "Luta" not in dice.describe(dice.hidden(r))


# ------------------------------------------------------------------ testes de Ordem
@pytest.mark.parametrize("n, mode, extra", [(0, "desvantagem", 1), (1, "normal", 0), (3, "vantagem", 2)])
def test_teste_rola_n_d20_e_fica_com_o_melhor(n, mode, extra):
    req = ordem.teste_request(n, 5)
    assert (req["sides"], req["qty"], req["mode"], req["extra"], req["bonus"]) == (20, 1, mode, extra, 5)


@pytest.mark.parametrize("texto, esperado", [
    ("3d20+15", (3, 15)), ("Luta 2d20+5", (2, 5)), ("d20", (1, 0)), ("1d20-1", (1, -1)), ("2d20↓", (0, 0)),
    ("2D20 + 3", (2, 3)), ("Ocultismo", None), ("Luta", None), ("O Amor", None),
    ("3O+15", (3, 15)), ("O+5", (1, 5)),  # notação do livro ainda é entendida
])
def test_le_o_teste(texto, esperado):
    assert ordem.parse_teste(texto) == esperado


@pytest.mark.parametrize("n, bonus, texto", [(3, 10, "3d20+10"), (1, 0, "1d20"), (0, 2, "2d20↓+2"), (2, -1, "2d20-1")])
def test_escreve_o_dado_inteiro(n, bonus, texto):
    assert ordem.fmt_teste(n, bonus) == texto
    assert ordem.parse_teste(texto) == (n, bonus)


@pytest.mark.parametrize("antes, depois", [
    ("2O+10", "2d20+10"), ("Luta 3O+10", "Luta 3d20+10"), ("O", "1d20"), ("Vontade O+5", "Vontade 1d20+5"),
    ("0O", "2d20↓"), ("O Amor ataca", "O Amor ataca"), ("Fortitude 3O+10, Reflexos 2O+5", "Fortitude 3d20+10, Reflexos 2d20+5"),
])
def test_converte_a_notacao_do_livro(antes, depois):
    assert ordem.d20_notation(antes) == depois


def test_ficha_antiga_de_ameaca_e_convertida_ao_abrir():
    s = ameaca(testes={"vontade": "O+5", "luta": "x"}, pericias="Luta 3O+10",
               acoes=[{"nome": "Garras", "teste": "Luta 2O+5", "descricao": "Fortitude 2O+5 evita. O Pai foge."}])
    assert s["testes"]["vontade"] == "1d20+5" and s["pericias"] == "Luta 3d20+10"
    assert s["acoes"][0]["teste"] == "Luta 2d20+5"
    assert s["acoes"][0]["descricao"] == "Fortitude 2d20+5 evita. O Pai foge."


def test_pericia_do_agente_usa_atributo_e_bonus():
    s = agente(pericias={"luta": {"treino": 5, "outros": 1}})
    req = ordem.pericia_request(s, "luta")
    assert (req["mode"], req["extra"], req["bonus"], req["label"]) == ("vantagem", 2, 6, "Luta")


def test_ataque_do_agente_pelo_nome_da_pericia():
    s = agente(pericias={"pontaria": {"treino": 10}})
    req = ordem.ataque_request(s, "Pontaria +2", "Pistola")
    assert (req["extra"], req["bonus"], req["label"]) == (1, 12, "Pistola")
    assert ordem.ataque_request(s, "+3")["bonus"] == 3
    assert ordem.ataque_request(s, "arma") is None


def test_iniciativa_do_agente_com_vigor_zero_nao_interfere():
    s = agente(pericias={"iniciativa": {"treino": 5}})
    req = ordem.iniciativa_request(s)
    assert (req["extra"], req["bonus"]) == (1, 5)


# ------------------------------------------------------------------ rituais
def test_rituais_normalizados_e_custo_por_circulo():
    s = agente(rituais=[{"nome": "Decadência", "elemento": "morte", "circulo": "2", "pagina": "pág. 127"},
                        {"nome": ""}])
    assert len(s["rituais"]) == 1
    r = s["rituais"][0]
    assert (r["elemento"], r["circulo"], r["pagina"], r["dano"]) == ("Morte", 2, "127", "")
    assert [ordem.custo_ritual({"circulo": c}) for c in (1, 2, 3, 4)] == [1, 3, 6, 10]


# ------------------------------------------------------------------ ameaças
def test_ameaca_nova_tem_os_campos_do_livro(tmp_path):
    s = create_new_threat("Zumbi de Sangue", str(tmp_path / "z.json"))
    assert ordem.is_ameaca(s)
    assert s["testes"] == {k: "1d20" for k in ("percepcao", "iniciativa", "fortitude", "reflexos", "vontade")}
    assert s["tamanho"] == "Médio" and s["deslocamento"] == "9m"
    assert "pericias" in s and "pe" not in s and "san" not in s
    assert ordem.is_ameaca(load_sheet(str(tmp_path / "z.json")))


def test_ameaca_pv_limitado_e_machucado():
    s = ameaca(pv={"max": 50, "atual": 80})
    assert s["pv"] == {"max": 50, "atual": 50}
    assert ordem.machucado(s) == 25


def test_ameaca_rola_testes_pericias_escritas_e_ataques():
    s = ameaca(atributos={"agi": 2, "for": 3}, testes={"iniciativa": "2d20+15"},
               pericias="Furtividade 2d20+13, Luta 3d20+15")
    assert ordem.pericias_ameaca(s) == [("Furtividade", 2, 13), ("Luta", 3, 15)]
    assert ordem.iniciativa_request(s)["bonus"] == 15
    assert ordem.ataque_request(s, "Luta")["bonus"] == 15          # acha a perícia escrita
    assert ordem.ataque_request(s, "Atletismo")["extra"] == 2      # sem valor: só o atributo (FOR 3)
    assert ordem.ataque_request(s, "3d20+10")["bonus"] == 10


def test_ameaca_nao_vai_para_jogador(tmp_path):
    server = DNDServer(port=0, system="ordem")
    with pytest.raises(ValueError):
        server.assign_sheet("Sofia", str(tmp_path / "z.json"), ameaca())


def test_jogador_nao_transforma_a_ficha_em_ameaca(tmp_path):
    server = DNDServer(port=0, system="ordem")
    path = tmp_path / "sofia.json"
    sheet = agente(nome="Sofia")
    server.assign_sheet("Sofia", str(path), sheet)
    server._apply_player_update("Sofia", {**sheet, "tipo": "ameaca"})
    assert not ordem.is_ameaca(server.get_sheet("Sofia"))
    assert not path.exists() or "ameaca" not in json.loads(path.read_text(encoding="utf-8")).get("tipo", "")


# ------------------------------------------------------------------ estados do agente
def test_machucado_e_inconsciente():
    s = agente()
    s["pv"]["atual"] = s["pv"]["max"] // 2
    ordem.apply_rules(s)
    assert ordem.machucado_agente(s) and not ordem.inconsciente(s)
    assert ordem.estados_texto(s) == [("MACHUCADO", False)]


def test_morrendo_so_acaba_ao_estabilizar():
    s = agente()
    s["pv"]["atual"] = 0
    ordem.apply_rules(s)
    assert s["estados"]["morrendo"] and ordem.inconsciente(s)
    s["pv"]["atual"] = 3  # cura acaba com o inconsciente, não com o morrendo
    ordem.apply_rules(s)
    assert s["estados"]["morrendo"] and not ordem.inconsciente(s)
    s["estados"]["turnos_morrendo"] = 2
    ordem.estabilizar(s)
    ordem.apply_rules(s)
    assert not s["estados"]["morrendo"] and s["pv"]["atual"] == 3
    assert s["estados"]["turnos_morrendo"] == 2  # conta na cena toda
    ordem.nova_cena(s)
    assert s["estados"]["turnos_morrendo"] == 0


def test_estabilizar_com_0_pv_fica_com_1_e_nao_volta_a_morrer():
    s = agente()
    s["pv"]["atual"] = 0
    ordem.apply_rules(s)
    ordem.estabilizar(s)
    ordem.apply_rules(s)
    assert s["pv"]["atual"] == 1 and not s["estados"]["morrendo"]


def test_tres_turnos_morrendo_e_morte():
    s = agente()
    s["pv"]["atual"] = 0
    s["estados"]["turnos_morrendo"] = 7
    ordem.apply_rules(s)
    assert s["estados"]["turnos_morrendo"] == 3 and ordem.morto(s)
    assert ordem.estados_texto(s)[0] == ("MORTO", True)


def test_enlouquecendo_acaba_com_cura_de_san_ou_acalmar():
    s = agente()
    s["san"]["atual"] = 0
    ordem.apply_rules(s)
    assert s["estados"]["enlouquecendo"]
    assert ("ENLOUQUECENDO 0/3", True) in ordem.estados_texto(s)
    s["san"]["atual"] = 1
    ordem.apply_rules(s)
    assert not s["estados"]["enlouquecendo"]
    s["san"]["atual"] = 0
    ordem.apply_rules(s)
    ordem.acalmar(s)
    ordem.apply_rules(s)
    assert s["san"]["atual"] == 1 and not s["estados"]["enlouquecendo"]


def test_estados_sobrevivem_ao_salvar(tmp_path):
    s = agente()
    s["pv"]["atual"] = 0
    ordem.apply_rules(s)
    again = normalize_sheet(s)
    assert again["estados"]["morrendo"] and again["estados"]["pv_zerado"]


def test_estados_na_barra_lateral():
    from src.ui.systems import states
    ameaca = normalize_sheet({"sistema": "ordem", "tipo": "ameaca", "pv": {"max": 20, "atual": 0}})
    assert states(ameaca) == [("DERROTADA", True)]
    pc = normalize_sheet({"sistema": "dnd5e", "combate": {"hp_max": 10, "hp_atual": 0,
                                                          "morte": {"sucessos": 1, "falhas": 2}}})
    assert states(pc) == [("CAÍDO  ✓1 ✗2", True)]
    assert states(normalize_sheet({"sistema": "dnd5e", "combate": {"hp_max": 10}})) == []


# ------------------------------------------------------------------ condições
def test_condicoes_normalizadas_sem_repetir():
    s = agente(condicoes=["Caído", "abalado", "inventada", "caido", "Em Chamas"])
    assert s["condicoes"] == ["caido", "abalado", "em_chamas"]
    assert ordem.condicoes_texto(s) == "caído, abalado, em chamas"
    assert normalize_sheet({"sistema": "ordem", "tipo": "ameaca", "condicoes": ["Lento"]})["condicoes"] == ["lento"]


@pytest.mark.parametrize("repeticoes, fica", [
    (["abalado"], ["abalado"]), (["abalado", "abalado"], ["apavorado"]),
    (["abalado", "abalado", "abalado"], ["apavorado"]),
    (["fatigado", "fatigado"], ["exausto"]), (["fatigado"] * 3, ["inconsciente"]),
    (["fraco", "fraco", "fraco"], ["inconsciente"]), (["frustrado", "frustrado"], ["esmorecido"]),
    (["caido", "caido"], ["caido"]), (["exausto", "fatigado"], ["inconsciente"]),
])
def test_condicao_repetida_piora(repeticoes, fica):
    s = agente()
    for key in repeticoes:
        ordem.adicionar_condicao(s, key)
    assert s["condicoes"] == fica


def test_remover_condicao_e_barra_lateral():
    from src.ui.systems import states
    s = agente()
    ordem.adicionar_condicao(s, "caido")
    ordem.adicionar_condicao(s, "vulneravel")
    assert states(s) == [("caído, vulnerável", False)]
    ordem.remover_condicao(s, "caido")
    ordem.remover_condicao(s, "caido")
    assert s["condicoes"] == ["vulneravel"]


def test_todas_as_condicoes_tem_resumo_e_piora_valida():
    for key, nome, resumo, piora in ordem.CONDICOES:
        assert nome and resumo and (piora is None or piora in ordem.CONDICAO)
    assert not {"machucado", "morrendo", "enlouquecendo"} & set(ordem.CONDICAO)


# ------------------------------------------------------------------ penalidades das condições
def com(*condicoes, **kw):
    return agente(condicoes=list(condicoes), **kw)


def dados_do(req):
    """Quantos d20 o pedido rola (0 = 2d20 e fica com o pior)."""
    return 0 if req["mode"] == "desvantagem" else 1 + req["extra"]


def test_sem_condicao_nada_muda():
    s = com()
    assert ordem.penalidade_dados(s, "luta") == (0, [])
    assert dados_do(ordem.pericia_request(s, "luta")) == 3
    assert ordem.pericia_request(s, "luta")["label"] == "Luta"


def test_abalado_tira_um_dado_de_todo_teste():
    s = com("abalado")
    assert dados_do(ordem.pericia_request(s, "luta")) == 2
    assert dados_do(ordem.pericia_request(s, "pontaria")) == 1
    assert ordem.pericia_request(s, "luta")["label"] == "Luta (−1d20: abalado)"
    assert ordem.dados_pericia(s, "luta") == "2d20"


def test_mesma_linha_vale_a_pior_e_linhas_diferentes_somam():
    s = com("abalado", "debilitado", "fatigado")  # fatigado inclui fraco: fraco e debilitado = só −2
    assert ordem.penalidade_dados(s, "atletismo") == (3, ["abalado", "debilitado"])
    assert ordem.penalidade_dados(s, "diplomacia") == (1, ["abalado"])


def test_zero_dados_vira_2d20_pior():
    s = com("abalado")  # PRE 1
    req = ordem.pericia_request(s, "diplomacia")
    assert req["mode"] == "desvantagem" and dados_do(req) == 0
    assert ordem.dados_pericia(s, "diplomacia") == "2d20↓"


def test_ataques_caido_so_corpo_a_corpo():
    s = com("caido")
    assert dados_do(ordem.ataque_request(s, "Luta", "Faca")) == 1
    assert dados_do(ordem.ataque_request(s, "Pontaria", "Revólver")) == 2
    assert dados_do(ordem.pericia_request(s, "luta")) == 3  # teste de Luta que não é ataque: sem penalidade
    s = com("ofuscado")
    assert dados_do(ordem.ataque_request(s, "Pontaria", "Revólver")) == 1
    assert dados_do(ordem.pericia_request(s, "percepcao")) == 0
    assert dados_do(ordem.ataque_request(s, "3d20+5", "Garra")) == 2  # dado escrito também perde


def test_testes_especificos():
    assert dados_do(ordem.pericia_request(com("surdo"), "iniciativa")) == 0
    assert dados_do(ordem.pericia_request(com("desprevenido"), "reflexos")) == 1
    assert dados_do(ordem.pericia_request(com("cego"), "acrobacia")) == 0
    # Reflexos é de AGI: cego tira 2 e o desprevenido que ele inclui tira mais 1
    assert ordem.penalidade_dados(com("cego"), "reflexos") == (3, ["cego", "desprevenido"])
    assert dados_do(ordem.pericia_request(com("frustrado"), "investigacao")) == 0


def test_defesa():
    base = ordem.defesa_total(com())
    assert ordem.defesa_total(com("desprevenido")) == base - 5
    assert ordem.defesa_total(com("vulneravel")) == base - 2
    assert ordem.defesa_total(com("atordoado", "vulneravel")) == base - 7
    assert ordem.defesa_total(com("paralisado")) == base - 10  # indefeso no lugar de desprevenido
    assert ordem.defesa_total(com("exausto")) == base - 2
    s = com()
    s["pv"]["atual"] = 0
    ordem.apply_rules(s)
    assert ordem.defesa_total(s) == base - 10  # 0 PV: inconsciente, logo indefeso


def test_ameaca_tambem_sofre():
    s = normalize_sheet({"sistema": "ordem", "tipo": "ameaca", "defesa": 18, "testes": {"reflexos": "2d20+5"},
                         "condicoes": ["desprevenido", "vulneravel"]})
    assert ordem.defesa_ameaca(s) == 11
    req = ordem.ameaca_pericia_request(s, "reflexos")
    assert dados_do(req) == 1 and req["bonus"] == 5
    s["condicoes"] = ["agarrado"]
    assert dados_do(ordem.ataque_request(s, "Luta 3d20+10", "Mordida")) == 2


# ------------------------------------------------------------------ trilhas e afinidade
def test_trilhas_da_classe_e_nomes():
    assert [n for _, n, *_ in ordem.trilhas_da_classe(agente())][0] == "Aniquilador"
    assert all(len(info[3]) == 4 for info in ordem.TRILHA.values()) and len(ordem.TRILHA) == 15
    assert agente(trilha="Tropa de Choque")["trilha"] == "tropa"
    assert agente(trilha="tropa", classe="Especialista")["trilha"] == ""  # trilha de outra classe sai
    assert agente(trilha="inventada")["trilha"] == ""


def test_habilidades_liberadas_pelo_nex():
    s = agente(trilha="guerreiro", nex=40)
    assert [(nex, tem) for nex, _, tem, _ in ordem.habilidades_trilha(s)] == [
        (10, True), (40, True), (65, False), (99, False)]
    assert ordem.habilidades_trilha(agente()) == []


def test_casca_grossa_e_iniciativa_aprimorada():
    sem, com_trilha = agente(nex=40), agente(nex=40, trilha="tropa")
    assert com_trilha["pv"]["max"] - sem["pv"]["max"] == 8  # NEX 40% = 8 níveis de 5%
    assert agente(nex=5, trilha="tropa")["pv"]["max"] == agente(nex=5)["pv"]["max"]  # antes de NEX 10%
    assert ordem.bonus_pericia(agente(nex=10, trilha="operacoes"), "iniciativa") == 5


def test_inventario_otimizado():
    s = agente(classe="Especialista", nex=10, trilha="tecnico", atributos={"for": 1, "int": 3})
    assert s["inventario"]["carga_max"] == 20


def test_inquebravel():
    s = agente(nex=99, trilha="tropa")
    base = ordem.defesa_total(s)
    s["pv"]["atual"] = s["pv"]["max"] // 2
    ordem.apply_rules(s)
    assert ordem.defesa_total(s) == base + 5
    s["pv"]["atual"] = 0
    ordem.apply_rules(s)
    assert "indefeso" not in ordem.condicoes_efetivas(s)  # morrendo, mas não indefeso


def test_afinidade():
    assert agente(afinidade="sangue")["afinidade"] == "Sangue"
    assert agente(afinidade="Medo")["afinidade"] == ""  # Medo não é afinidade
