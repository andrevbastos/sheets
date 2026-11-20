from src import ordem
from src.sheet_io import create_new_sheet, load_sheet, normalize_sheet


def test_ficha_nova_de_ordem(tmp_path):
    sheet = create_new_sheet("Arthur", "ordem", str(tmp_path / "a.json"))
    assert sheet["sistema"] == "ordem"
    assert sheet["nome"] == "Arthur"
    assert sheet["atributos"] == {"agi": 1, "for": 1, "int": 1, "pre": 1, "vig": 1}
    assert set(sheet["pericias"]) == {k for k, *_ in ordem.PERICIAS}
    assert sheet["pv"] == {"max": 0, "atual": 0}
    assert sheet["inventario"]["itens"] == []
    assert "{{" not in (tmp_path / "a.json").read_text(encoding="utf-8")


def test_exemplo_de_ordem_e_calculos_da_ficha():
    sheet = load_sheet("sheets/ordem-example.json")
    assert sheet["sistema"] == "ordem"
    assert ordem.defesa_total(sheet) == 11            # 10 + AGI 1 + 0 + 0
    assert ordem.bonus_pericia(sheet, "ocultismo") == 7  # treino 5 + outros 2
    assert ordem.bonus_pericia(sheet, "luta") == 0     # perícia ausente no JSON vira 0
    assert ordem.espacos_usados(sheet) == 3


def test_normalizacao_de_ordem_limita_valores():
    sheet = normalize_sheet({
        "sistema": "ordem",
        "nex": "150",
        "pv": {"atual": "30", "max": "20"},
        "atributos": {"agi": "-2", "int": "4"},
        "ataques": [{"nome": ""}, {"nome": "Faca", "dano": "1d4"}],
    })
    assert sheet["nex"] == 100
    assert sheet["pv"] == {"max": 20, "atual": 20}
    assert sheet["atributos"]["agi"] == 0 and sheet["atributos"]["int"] == 4
    assert sheet["ataques"] == [{"nome": "Faca", "teste": "", "dano": "1d4", "especial": ""}]


def test_dnd_continua_dnd():
    assert normalize_sheet({"nome": "x"})["sistema"] == "dnd5e"
