import pytest

from src import ordem
from src.sheet_io import create_new_sheet, load_sheet, normalize_sheet


def ficha(**kw):
    base = {"sistema": "ordem", "classe": "", "nex": 5,
            "atributos": {"agi": 1, "for": 1, "int": 1, "pre": 1, "vig": 1}}
    base.update(kw)
    return normalize_sheet(base)


def test_ficha_nova_de_ordem(tmp_path):
    sheet = create_new_sheet("Arthur", "ordem", str(tmp_path / "a.json"))
    assert sheet["sistema"] == "ordem"
    assert sheet["nome"] == "Arthur"
    assert sheet["atributos"] == {"agi": 1, "for": 1, "int": 1, "pre": 1, "vig": 1}
    assert set(sheet["pericias"]) == {k for k, *_ in ordem.PERICIAS}
    assert sheet["pv"] == {"max": 0, "atual": 0, "bonus": 0}  # sem classe: digitado à mão
    assert sheet["inventario"]["patente"] == "Recruta"
    assert "{{" not in (tmp_path / "a.json").read_text(encoding="utf-8")


@pytest.mark.parametrize("classe, pv, pe, san", [
    # NEX 5%, VIG 2, PRE 3 (valores iniciais, p. 35/39/43)
    ("Combatente", 20 + 2, 2 + 3, 12),
    ("Especialista", 16 + 2, 3 + 3, 16),
    ("Ocultista", 12 + 2, 4 + 3, 20),
])
def test_valores_iniciais_por_classe(classe, pv, pe, san):
    s = ficha(classe=classe, atributos={"agi": 1, "for": 1, "int": 1, "pre": 3, "vig": 2})
    assert (s["pv"]["max"], s["pe"]["max"], s["san"]["max"]) == (pv, pe, san)
    assert s["pv"]["atual"] == pv  # ficha nova começa cheia


def test_progressao_por_nex():
    # Combatente NEX 50% = 10 níveis: PV 20+VIG + 9*(4+VIG), PE 2+PRE + 9*(2+PRE), SAN 12 + 9*3
    s = ficha(classe="combatente", nex=50, atributos={"agi": 1, "for": 1, "int": 1, "pre": 2, "vig": 3})
    assert s["pv"]["max"] == 23 + 9 * 7
    assert s["pe"]["max"] == 4 + 9 * 4
    assert s["san"]["max"] == 12 + 27
    assert s["pe_rodada"] == 10


def test_exemplos_de_dt_do_livro():
    # p. 131: Presença 3 e NEX 5% -> DT 14; Presença 5 e NEX 99% -> DT 35
    assert ficha(atributos={"agi": 1, "for": 1, "int": 1, "pre": 3, "vig": 1})["dt_rituais"] == 14
    assert ficha(nex=99, atributos={"agi": 1, "for": 1, "int": 1, "pre": 5, "vig": 1})["dt_rituais"] == 35


def test_nex_vira_nivel_valido():
    assert ficha(nex=12)["nex"] == 10
    assert ficha(nex=100)["nex"] == 99
    assert ficha(nex=0)["nex"] == 5


def test_bonus_de_poder_soma_no_maximo():
    s = ficha(classe="Ocultista", pe={"bonus": 2})
    assert s["pe"]["max"] == 4 + 1 + 2


def test_carga_e_sobrecarga():
    assert ficha(atributos={"agi": 1, "for": 0, "int": 1, "pre": 1, "vig": 1})["inventario"]["carga_max"] == 2
    s = ficha(atributos={"agi": 2, "for": 1, "int": 1, "pre": 1, "vig": 1},
              inventario={"itens": [{"nome": "Caixote", "espacos": 6}]},
              pericias={"acrobacia": {"treino": 5}, "luta": {"treino": 5}})
    assert ordem.sobrecarregado(s)
    assert ordem.defesa_total(s) == 10 + 2 - 5
    assert ordem.bonus_pericia(s, "acrobacia") == 0   # perícia de carga sofre −5
    assert ordem.bonus_pericia(s, "luta") == 5         # as outras não


def test_patente_pelo_prestigio():
    s = ficha(inventario={"pontos_prestigio": 58})
    assert s["inventario"]["patente"] == "Agente especial"
    assert s["inventario"]["limite_credito"] == "Médio"
    assert s["inventario"]["limite_itens"] == {"I": 3, "II": 2, "III": 1, "IV": 0}


def test_grau_de_treino_e_dados():
    s = ficha(pericias={"luta": {"treino": "7"}}, atributos={"agi": 1, "for": 0, "int": 1, "pre": 1, "vig": 1})
    assert s["pericias"]["luta"]["treino"] == 5      # arredonda para um grau válido
    assert ordem.dados(s, "for") == "2d20↓"          # atributo 0: 2d20, fica com o pior
    assert ordem.dados(s, "agi") == "1d20"


def test_exemplo_de_ordem():
    s = load_sheet("sheets/ordem-example.json")
    # Ocultista NEX 10%, VIG 1, PRE 2
    assert (s["pv"]["max"], s["pe"]["max"], s["san"]["max"]) == (16, 12, 25)
    assert s["pv"]["atual"] == 13
    assert s["dt_rituais"] == 14
    assert ordem.bonus_pericia(s, "ocultismo") == 7
    assert not ordem.sobrecarregado(s)


def test_classe_desconhecida_mantem_valores_digitados():
    s = ficha(classe="Mundano", pv={"max": 9, "atual": 4})
    assert s["pv"] == {"max": 9, "atual": 4, "bonus": 0}


def test_dnd_continua_dnd():
    assert normalize_sheet({"nome": "x"})["sistema"] == "dnd5e"
