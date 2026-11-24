"""Regras automáticas da ficha de D&D 5e (Livro do Jogador) e migração das fichas antigas."""
import json

import pytest

from src import dnd
from src.sheet_io import create_new_sheet, load_sheet, normalize_sheet


def ficha(**kw):
    base = {"sistema": "dnd5e", "classe": "Guerreiro", "nivel": 1,
            "atributos": {a: {"valor": 10} for a, *_ in dnd.ATRIBUTOS}}
    base.update(kw)
    return normalize_sheet(base)


@pytest.mark.parametrize("valor, mod", [(1, -5), (3, -4), (8, -1), (9, -1), (10, 0), (11, 0), (12, 1), (15, 2),
                                        (18, 4), (20, 5), (30, 10)])
def test_modificador_pela_tabela(valor, mod):
    assert dnd.modificador(valor) == mod


@pytest.mark.parametrize("nivel, bonus", [(1, 2), (4, 2), (5, 3), (8, 3), (9, 4), (13, 5), (16, 5), (17, 6), (20, 6)])
def test_bonus_de_proficiencia_por_nivel(nivel, bonus):
    assert dnd.bonus_proficiencia(nivel) == bonus


def test_pericias_proficiente_especialista_e_outros():
    s = ficha(nivel=5, atributos={"destreza": {"valor": 16}},
              pericias={"furtividade": {"grau": 2}, "acrobacia": {"grau": 1, "outros": 1}, "prestidigitacao": {}})
    assert s["pericias"]["furtividade"]["bonus"] == 3 + 2 * 3   # especialista dobra
    assert s["pericias"]["acrobacia"]["bonus"] == 3 + 3 + 1
    assert s["pericias"]["prestidigitacao"]["bonus"] == 3
    assert s["pericias"]["furtividade"]["proficiente"] is True


def test_resistencia_iniciativa_e_percepcao_passiva():
    s = ficha(atributos={"constituicao": {"valor": 14}, "destreza": {"valor": 8}, "sabedoria": {"valor": 15}},
              resistencia={"constituicao": {"proficiente": True}}, pericias={"percepcao": {"grau": 1}},
              combate={"iniciativa_outros": 5})
    assert s["resistencia"]["constituicao"]["bonus"] == 2 + 2
    assert s["resistencia"]["destreza"]["bonus"] == -1
    assert s["combate"]["iniciativa"] == -1 + 5             # talento Alerta
    assert s["combate"]["percepcao_passiva"] == 10 + 2 + 2  # p. 177: 10 + bônus de Percepção


@pytest.mark.parametrize("classe, atributo", [("Mago", "inteligencia"), ("Clérigo", "sabedoria"),
                                              ("Bruxo", "carisma"), ("Guerreiro / Mago", "inteligencia")])
def test_cd_e_ataque_de_magia_pela_classe(classe, atributo):
    s = ficha(classe=classe, nivel=5, atributos={atributo: {"valor": 18}})
    assert s["magias"]["cd_salvamento"] == 8 + 4 + 3
    assert s["magias"]["bonus_ataque"] == 4 + 3


def test_sem_atributo_de_conjuracao_cd_fica_digitada():
    s = ficha(classe="Guerreiro", magias={"cd_salvamento": 13, "bonus_ataque": 5})
    assert dnd.atributo_conjuracao(s) is None
    assert (s["magias"]["cd_salvamento"], s["magias"]["bonus_ataque"]) == (13, 5)
    s = ficha(classe="Guerreiro", magias={"atributo": "sabedoria"})  # Cavaleiro Arcano, magia de item...
    assert s["magias"]["cd_salvamento"] == 8 + 0 + 2


def test_ficha_antiga_mantem_os_numeros():
    """Fichas antigas guardavam o bônus final; a diferença vira "outros"."""
    antiga = json.load(open("sheets/dnd-example.json", encoding="utf-8"))
    s = load_sheet("sheets/dnd-example.json")
    assert (s["classe"], s["nivel"]) == ("Guerreiro", 1)
    assert "classe_nivel" not in s
    for key, p in antiga["pericias"].items():
        assert s["pericias"][key]["bonus"] == p["bonus"], key
    for attr, r in antiga["resistencia"].items():
        assert s["resistencia"][attr]["bonus"] == r["bonus"], attr
    assert s["combate"]["iniciativa"] == antiga["combate"]["iniciativa"]
    assert s["idiomas"] == "Comum, Anão"


def test_bonus_antigo_diferente_do_calculado_vira_outros():
    s = normalize_sheet({"classe_nivel": "Ladino 3 / Mago 2", "atributos": {"destreza": {"valor": 14, "mod": 2}},
                         "pericias": {"furtividade": {"bonus": 9, "proficiente": True}},
                         "combate": {"iniciativa": 7}})
    assert (s["classe"], s["nivel"]) == ("Ladino / Mago", 5)
    assert s["pericias"]["furtividade"]["outros"] == 9 - (2 + 3)
    assert s["pericias"]["furtividade"]["bonus"] == 9
    assert s["combate"]["iniciativa_outros"] == 5


def test_ficha_nova_comeca_preenchivel(tmp_path):
    s = create_new_sheet("Gimli", "dnd5e", str(tmp_path / "g.json"))
    assert (s["classe"], s["nivel"], s["combate"]["proficiencia"]) == ("", 1, 2)
    assert all(a["valor"] == 10 and a["mod"] == 0 for a in s["atributos"].values())
    assert all(p == {"grau": 0, "outros": 0, "proficiente": False, "bonus": 0} for p in s["pericias"].values())
    assert s["magias"]["atributo"] == ""


# ------------------------------------------------------------------ rolagens (fase 2)
def test_rolagens_de_pericia_resistencia_atributo_e_iniciativa():
    s = ficha(nivel=5, atributos={"forca": {"valor": 16}, "destreza": {"valor": 14}},
              pericias={"atletismo": {"grau": 2}}, resistencia={"forca": {"proficiente": True}})
    assert dnd.pericia_request(s, "atletismo") == {"sides": 20, "qty": 1, "mode": "normal", "extra": 0,
                                                   "bonus": 3 + 6, "label": "Atletismo"}
    assert dnd.resistencia_request(s, "forca")["bonus"] == 3 + 3
    assert dnd.atributo_request(s, "destreza")["label"] == "Teste de Destreza"
    assert dnd.iniciativa_request(s)["bonus"] == 2


@pytest.mark.parametrize("texto, bonus", [("+5", 5), ("5", 5), ("-1", -1), ("FOR", 3 + 2), ("DES +1", 2 + 2 + 1),
                                          ("for", 5), ("", None), ("arco", None)])
def test_jogada_de_ataque(texto, bonus):
    s = ficha(atributos={"forca": {"valor": 16}, "destreza": {"valor": 14}})
    req = dnd.ataque_request(s, texto, "Espada")
    assert (req and req["bonus"]) == bonus


@pytest.mark.parametrize("texto, esperado", [("2d6+3 cortante", (2, 6, 3)), ("1d8+FOR", (1, 8, 3)),
                                             ("1d8 - FOR", (1, 8, -3)), ("1d4+DES perfurante", (1, 4, 2))])
def test_dano_com_modificador(texto, esperado):
    s = ficha(atributos={"forca": {"valor": 16}, "destreza": {"valor": 14}})
    req = dnd.dano_request(s, texto)
    assert (req["qty"], req["sides"], req["bonus"]) == esperado


def test_ataque_antigo_vira_campos_de_ataque_e_dano():
    s = ficha(ataques=[{"nome": "Espada", "descricao": "Bônus: +5 | Dano: 2d6+3 (Cortante)"},
                       {"nome": "Rede", "descricao": "Agarra o alvo"}])
    assert s["ataques"][0] == {"nome": "Espada", "ataque": "+5", "dano": "2d6+3 (Cortante)", "descricao": ""}
    assert s["ataques"][1] == {"nome": "Rede", "ataque": "", "dano": "", "descricao": "Agarra o alvo"}


def test_shift_da_vantagem_no_dnd_e_mais_um_dado_no_ordem():
    from src import ordem
    from src.ui.ordem_sheet import SheetView as OrdemView
    from src.ui.sheet_base import BaseSheetView

    req = dnd.pericia_request(ficha(), "acrobacia")
    assert BaseSheetView._roll_variant(req, "mais")["mode"] == "vantagem"
    assert BaseSheetView._roll_variant(req, "menos")["mode"] == "desvantagem"
    dois = ordem.teste_request(2, 5, "Luta")
    assert OrdemView._roll_variant(dois, "mais")["extra"] == 2      # 3d20
    assert OrdemView._roll_variant(dois, "menos")["mode"] == "normal"  # 1d20
    assert OrdemView._roll_variant(ordem.teste_request(1, 0), "menos")["mode"] == "desvantagem"  # 0 dados: pior de 2


# ------------------------------------------------------------------ vida, morte e descanso (fase 3)
def ferido(**combate):
    base = {"hp_max": 20, "hp_atual": 20}
    base.update(combate)
    return ficha(nivel=4, combate=base)


def test_dano_tira_primeiro_os_pv_temporarios():
    s = ferido(hp_temp=5)
    dnd.sofrer_dano(s, 7)  # exemplo da p. 198
    assert (s["combate"]["hp_atual"], s["combate"]["hp_temp"]) == (18, 0)


def test_dano_com_0_pv_e_falha_contra_a_morte_e_cura_zera():
    s = ferido(hp_atual=3)
    dnd.sofrer_dano(s, 10)
    assert s["combate"]["hp_atual"] == 0 and s["combate"]["morte"]["falhas"] == 0
    dnd.sofrer_dano(s, 1)
    assert s["combate"]["morte"]["falhas"] == 1
    dnd.curar(s, 4)
    assert s["combate"]["hp_atual"] == 4 and s["combate"]["morte"] == {"sucessos": 0, "falhas": 0}


@pytest.mark.parametrize("classe, dado", [("Bárbaro", "d12"), ("Guerreiro", "d10"), ("Ladino", "d8"),
                                          ("Mago", "d6"), ("Inventor", "")])
def test_dado_de_vida_pela_classe(classe, dado):
    s = ficha(classe=classe, nivel=3)
    assert s["combate"]["dados_vida"] == {"dado": dado, "restantes": 3}


def test_gastar_dado_de_vida_soma_constituicao():
    s = ficha(classe="Guerreiro", atributos={"constituicao": {"valor": 14}})
    req = dnd.dado_vida_request(s)
    assert (req["sides"], req["bonus"]) == (10, 2)
    s["combate"]["dados_vida"]["restantes"] = 0
    assert dnd.dado_vida_request(s) is None


def test_descansos():
    s = ferido(hp_atual=5, hp_temp=3, dados_vida={"dado": "d10", "restantes": 0}, morte={"sucessos": 1})
    s["recursos"] = [{"nome": "Fúria", "atual": 0, "max": 2, "recupera": "longo", "detalhes": ""},
                     {"nome": "Retomar o Fôlego", "atual": 0, "max": 1, "recupera": "curto", "detalhes": ""},
                     {"nome": "Poção", "atual": 0, "max": 3, "recupera": "", "detalhes": ""}]
    s["magias"]["slots"]["1"] = {"atual": 0, "max": 3}
    dnd.descanso_curto(s)
    assert [r["atual"] for r in s["recursos"]] == [0, 1, 0]
    assert dnd.descanso_longo(s)
    c = s["combate"]
    assert (c["hp_atual"], c["hp_temp"], c["morte"]["sucessos"]) == (20, 0, 0)
    assert c["dados_vida"]["restantes"] == 2  # metade do nível 4
    assert s["magias"]["slots"]["1"]["atual"] == 3
    assert [r["atual"] for r in s["recursos"]] == [2, 1, 0]


def test_descanso_longo_precisa_de_1_pv():
    s = ferido(hp_atual=0)
    assert dnd.descanso_longo(s) is False
    assert s["combate"]["hp_atual"] == 0


def test_recursos_antigos_da_aba_extra_viram_recursos():
    s = load_sheet("sheets/dnd-example.json")
    assert "recursos de classe" not in s["extra"]
    assert s["combate"]["dados_vida"]["dado"] == "d10"  # "Dado de Vida (d10)"
    nomes = {r["nome"]: r["recupera"] for r in s["recursos"]}
    assert nomes == {"Retomar o Fôlego": "curto", "Surto de Ação": ""}


def test_magias_tem_nivel():
    s = ficha(magias={"lista": [{"nome": "Bola de Fogo", "nivel": "3"}, {"nome": "Luz"}]})
    assert [m["nivel"] for m in s["magias"]["lista"]] == [3, 0]
