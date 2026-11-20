import json

from src.sheet_io import create_new_sheet, load_sheet, normalize_sheet, save_sheet

TEMPLATE = "sheets/sheet-template.json"


def test_ficha_nova_do_template_tem_numeros_e_listas_limpas(tmp_path):
    out = tmp_path / "Gimli.json"
    sheet = create_new_sheet("Gimli", TEMPLATE, str(out))

    assert sheet["nome"] == "Gimli"
    assert sheet["combate"]["hp_atual"] == 0 and sheet["combate"]["hp_max"] == 0
    assert sheet["atributos"]["forca"] == {"valor": 10, "mod": 0}
    assert sheet["pericias"]["acrobacia"]["proficiente"] is False
    assert sheet["inventario"] == []
    assert sheet["ataques"] == []
    assert sheet["extra"]["cartas_destino"]["lista"] == []
    assert sheet["extra"]["cartas_destino"]["maximo"] == 3
    assert "{{" not in out.read_text(encoding="utf-8")


def test_exemplo_carrega_sem_perder_dados():
    sheet = load_sheet("sheets/sheet-example.json")
    assert sheet["combate"]["hp_max"] == 12
    assert sheet["atributos"]["carisma"]["mod"] == -1
    assert len(sheet["inventario"]) == 7
    assert sheet["extra"]["cartas_destino"]["lista"][0]["nome"] == "O Sol"


def test_converte_custom_antigo_para_extra_e_strings_para_int():
    sheet = normalize_sheet({
        "combate": {"hp_max": "20", "hp_atual": "25", "ca": "+3"},
        "custom": {"cartas_destino": {"maximo": "2", "lista": []}},
    })
    assert "custom" not in sheet
    assert sheet["extra"]["cartas_destino"]["maximo"] == 2
    assert sheet["combate"]["hp_max"] == 20
    assert sheet["combate"]["hp_atual"] == 20  # limitado ao máximo
    assert sheet["combate"]["ca"] == 3


def test_save_sheet_grava_utf8_e_nao_deixa_temporario(tmp_path):
    path = tmp_path / "sub" / "f.json"
    save_sheet({"nome": "Ação"}, str(path))
    assert json.loads(path.read_text(encoding="utf-8")) == {"nome": "Ação"}
    assert [p.name for p in path.parent.iterdir()] == ["f.json"]
