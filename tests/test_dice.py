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
    req = dice.clean_request({"sides": 20, "mode": "vantagem", "extra": 1, "bonus": 5, "label": "Ataque"})
    r = dice.roll(req, "Sofia", Fixed([12, 9]))
    assert r["total"] == 17
    assert dice.describe(r) == "Sofia — Ataque: 1d20 (Van 1) + 5 → [12, (9)] = 17"


def test_desvantagem_com_varios_extras_fica_com_o_menor():
    req = dice.clean_request({"sides": 20, "mode": "desvantagem", "extra": 2, "bonus": -1})
    r = dice.roll(req, "Mestre", Fixed([15, 3, 8]))
    assert r["total"] == 2
    assert dice.describe(r) == "Mestre: 1d20 (Des 2) - 1 → [(15), 3, (8)] = 2"


def test_rolagem_privada_escondida():
    req = dice.clean_request({"sides": 20, "private": True})
    r = dice.roll(req, "Mestre", Fixed([20]))
    assert dice.describe(r) == "Mestre (privada): 1d20 → [20] = 20"
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
