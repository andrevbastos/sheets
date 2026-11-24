"""Escolhe a tela certa para cada sistema de RPG, pela chave "sistema" da ficha.

Para adicionar um sistema novo: criar src/ui/<sistema>_sheet.py com uma classe
SheetView(master, sheet, on_change) que tenha set_sheet(sheet), registrar aqui,
e adicionar o template em src/sheet_io.SYSTEMS.
"""
from src import dnd, ordem
from src.ui import ameaca_sheet, dnd5e_sheet, monstro_sheet, ordem_sheet

SYSTEMS = {
    dnd5e_sheet.SYSTEM: dnd5e_sheet.SheetView,
    ordem_sheet.SYSTEM: ordem_sheet.SheetView,
}


def make_sheet_view(master, sheet: dict, on_change=None, on_roll=None):
    """`on_roll(pedido)` recebe as rolagens pedidas pelos botões da ficha."""
    system = sheet.get("sistema", dnd5e_sheet.SYSTEM)
    if ordem.is_ameaca(sheet):
        return ameaca_sheet.SheetView(master, sheet, on_change=on_change, on_roll=on_roll)
    if dnd.is_monstro(sheet):
        return monstro_sheet.SheetView(master, sheet, on_change=on_change, on_roll=on_roll)
    view_class = SYSTEMS.get(system)
    if view_class is None:
        raise ValueError(f"Sistema de ficha desconhecido: {system!r}")
    return view_class(master, sheet, on_change=on_change, on_roll=on_roll)


def is_dm_only(sheet) -> bool:
    """Ficha só do mestre (ameaça de Ordem, monstro de D&D): não vai para jogadores."""
    return ordem.is_ameaca(sheet) or dnd.is_monstro(sheet)


def iniciativa_request(sheet: dict):
    """Pedido de rolagem de iniciativa da ficha (qualquer sistema)."""
    if sheet.get("sistema") == ordem_sheet.SYSTEM:
        return ordem.iniciativa_request(sheet)
    return dnd.iniciativa_request(sheet)


def resources(sheet: dict):
    """Recursos para resumos como a barra lateral do mestre: [(sigla, atual, máximo, cor ou None)].

    Cor None = verde/vermelho conforme o quanto resta.
    """
    if sheet.get("sistema") == ordem_sheet.SYSTEM:
        keys = (("pv", "PV"),) if ordem.is_ameaca(sheet) else (("pv", "PV"), ("san", "SAN"))
        return [(sigla, sheet.get(key, {}).get("atual", 0), sheet.get(key, {}).get("max", 0),
                 ordem_sheet.RESOURCE_COLORS[key])
                for key, sigla in keys]
    combate = sheet.get("combate", {})
    return [("HP", combate.get("hp_atual", 0), combate.get("hp_max", 0), None)]
