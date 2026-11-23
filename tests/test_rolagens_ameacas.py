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
