import random

import pytest

from src import dice


class Fixed(random.Random):
    """'Sorteio' com valores pré-definidos para testar a lógica."""

    def __init__(self, values):
        super().__init__()
        self.values = list(values)

    def randint(self, a, b):
        return self.values.pop(0)


def test_rolagem_normal_soma_tudo():
    req = dice.clean_request({"sides": 6, "qty": 3, "bonus": 2})
    r = dice.roll(req, "Sofia", Fixed([1, 4, 6]))
    assert r["total"] == 13
    assert dice.describe(r) == "Sofia: 3d6 + 2 → [1, 4, 6] = 13"


def test_vantagem_fica_com_o_maior():
    req = dice.clean_request({"sides": 20, "mode": "vantagem", "extra": 1, "bonus": 5})
    r = dice.roll(req, "Sofia", Fixed([12, 9]))
    assert r["total"] == 17
    assert dice.describe(r) == "Sofia: 1d20 (Van 1) + 5 → [12, (9)] = 17"


def test_20_natural_e_sucesso_critico_e_1_e_falha():
    d20 = dice.clean_request({"sides": 20, "bonus": 3})
    r = dice.roll(d20, "Sofia", Fixed([20]))
    assert r["critical"] == dice.CRIT_SUCCESS
    assert dice.describe(r) == "Sofia: 1d20 + 3 → [20] = 23 — SUCESSO CRÍTICO"
    assert dice.roll(d20, "Sofia", Fixed([1]))["critical"] == dice.CRIT_FAIL
    assert dice.roll(d20, "Sofia", Fixed([19]))["critical"] is None


def test_critico_vale_o_dado_que_ficou():
    van = dice.clean_request({"sides": 20, "mode": "vantagem", "extra": 1})
    assert dice.roll(van, "x", Fixed([1, 15]))["critical"] is None          # o 1 foi descartado
    des = dice.clean_request({"sides": 20, "mode": "desvantagem", "extra": 1})
    assert dice.roll(des, "x", Fixed([20, 1]))["critical"] == dice.CRIT_FAIL  # ficou o 1


def test_sem_critico_fora_de_1d20():
    assert dice.roll(dice.clean_request({"sides": 20, "qty": 2}), "x", Fixed([20, 20]))["critical"] is None
    assert dice.roll(dice.clean_request({"sides": 6}), "x", Fixed([6]))["critical"] is None


def test_rolagem_privada_escondida_nao_revela_critico():
    r = dice.roll(dice.clean_request({"sides": 20, "private": True}), "Mestre", Fixed([20]))
    assert dice.critical(dice.hidden(r)) is None
    assert "critical" not in dice.hidden(r)


def test_desvantagem_com_varios_extras_fica_com_o_menor():
    req = dice.clean_request({"sides": 20, "mode": "desvantagem", "extra": 2, "bonus": -1})
    r = dice.roll(req, "Mestre", Fixed([15, 3, 8]))
    assert r["total"] == 2
    assert dice.describe(r) == "Mestre: 1d20 (Des 2) - 1 → [(15), 3, (8)] = 2"


def test_rolagem_privada_escondida():
    req = dice.clean_request({"sides": 20, "private": True})
    r = dice.roll(req, "Mestre", Fixed([12]))
    assert dice.describe(r) == "Mestre (privada): 1d20 → [12] = 12"
    h = dice.hidden(r)
    assert "total" not in h and "rolled" not in h
    assert dice.describe(h) == "Mestre fez uma rolagem privada"


def test_pedido_invalido_e_limites():
    with pytest.raises(ValueError):
        dice.clean_request({"sides": 7})
    req = dice.clean_request({"sides": 20, "qty": 500, "mode": "vantagem", "extra": 99, "bonus": 10**6})
    assert (req["qty"], req["extra"], req["bonus"]) == (dice.MAX_QTY, dice.MAX_EXTRA, dice.MAX_BONUS)
    assert dice.clean_request({"sides": 20, "mode": "normal", "extra": 5})["extra"] == 0


def test_valores_ficam_no_intervalo_do_dado():
    req = dice.clean_request({"sides": 100, "qty": 20})
    r = dice.roll(req, "x")
    assert all(1 <= v <= 100 for v in r["rolled"])
