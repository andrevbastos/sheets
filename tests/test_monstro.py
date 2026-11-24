"""Ficha de monstro de D&D 5e (só do mestre): ND, proficiência, XP, perícias, PV e rolagens."""
import pytest

from src import dnd
from src.net.server import DNDServer
from src.sheet_io import create_new_threat, load_sheet, normalize_sheet
from src.ui.systems import is_dm_only, iniciativa_request, resources


def monstro(**kw):
    base = {"sistema": "dnd5e", "tipo": "monstro", "nome": "Goblin", "nd": "1/4",
            "atributos": {"forca": {"valor": 8}, "destreza": {"valor": 14}, "sabedoria": {"valor": 8}}}
    base.update(kw)
    return normalize_sheet(base)


@pytest.mark.parametrize("nd, prof, xp", [("0", 2, 10), ("1/8", 2, 25), ("1/4", 2, 50), ("1/2", 2, 100),
                                          ("4", 2, 1100), ("5", 3, 1800), ("8", 3, 3900), ("9", 4, 5000),
                                          ("13", 5, 10000), ("17", 6, 18000), ("21", 7, 33000),
                                          ("29", 9, 135000), ("30", 9, 155000)])
def test_proficiencia_e_xp_pelo_nd(nd, prof, xp):
    s = monstro(nd=nd)
    assert dnd.prof(s) == s["combate"]["proficiencia"] == prof
    assert s["xp"] == xp


def test_nd_invalido_vira_1_e_campos_existem():
    s = monstro(nd="abc")
    assert s["nd"] == "1" and s["tamanho"] == "Médio" and s["lendarias"] == {"max": 0, "atual": 0}
    assert "morte" not in s["combate"] and "pericias" in s and s["acoes"] == []


def test_resistencias_iniciativa_e_ataques_usam_proficiencia_do_nd():
    s = monstro(nd="5", resistencia={"destreza": {"proficiente": True}})
    assert dnd.bonus_resistencia(s, "destreza") == 2 + 3
    assert dnd.bonus_resistencia(s, "forca") == -1
    assert dnd.iniciativa_request(s)["bonus"] == 2
    assert dnd.ataque_request(s, "DES")["bonus"] == 5
    assert dnd.dano_request(s, "1d6+DES cortante")["bonus"] == 2


def test_pericias_escritas():
    s = monstro(pericias="Furtividade +6, Percepção, Inventada")
    assert dnd.pericias_monstro(s) == [("Furtividade", 6), ("Percepção", -1 + 2)]  # Inventada sem número: fora
    assert s["percepcao_passiva"] == 11
    assert monstro()["percepcao_passiva"] == 9  # sem Percepção escrita: 10 + Sabedoria


def test_pv_media_e_dano_sem_testes_contra_a_morte():
    assert dnd.pv_media("2d6") == 7
    assert dnd.pv_media("15d10+45") == 127
    assert dnd.pv_media("nada") is None
    s = monstro(combate={"hp_max": 7, "hp_temp": 2})
    dnd.sofrer_dano(s, 4)
    assert (s["combate"]["hp_atual"], s["combate"]["hp_temp"]) == (5, 0)
    dnd.sofrer_dano(s, 10)
    dnd.sofrer_dano(s, 1)  # já com 0 PV: nada quebra
    assert s["combate"]["hp_atual"] == 0
    dnd.curar(s, 3)
    assert s["combate"]["hp_atual"] == 3


def test_acoes_e_lendarias():
    s = monstro(acoes=[{"tipo": "Lendária", "nome": "Golpe de Cauda"}, {"tipo": "xyz", "nome": "Cimitarra"}],
                lendarias={"max": 3, "atual": 9})
    assert [a["tipo"] for a in s["acoes"]] == ["Lendária", "Ação"]
    assert s["lendarias"] == {"max": 3, "atual": 3}


def test_criar_monstro_e_regras_do_mestre(tmp_path):
    path = str(tmp_path / "goblin.json")
    s = create_new_threat("Goblin", path, "dnd5e")
    assert dnd.is_monstro(s) and is_dm_only(s) and dnd.is_monstro(load_sheet(path))
    assert iniciativa_request(s)["sides"] == 20
    assert resources(s) == [("HP", 0, 0, None)]
    with pytest.raises(ValueError):
        DNDServer(port=0, system="dnd5e").assign_sheet("Ana", path, s)


def test_ficha_de_personagem_nao_vira_monstro():
    s = normalize_sheet({"sistema": "dnd5e", "nome": "Ana"})
    assert not dnd.is_monstro(s) and not is_dm_only(s) and "morte" in s["combate"]
