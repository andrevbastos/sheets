"""Escolhe a tela certa para cada sistema de RPG, pela chave "sistema" da ficha.

Para adicionar um sistema novo: criar src/ui/<sistema>_sheet.py com uma classe
SheetView(master, sheet, on_change) que tenha set_sheet(sheet), registrar aqui,
e adicionar o template em src/sheet_io.SYSTEMS.
"""
from src.ui import dnd5e_sheet, ordem_sheet

SYSTEMS = {
    dnd5e_sheet.SYSTEM: dnd5e_sheet.SheetView,
    ordem_sheet.SYSTEM: ordem_sheet.SheetView,
}


def make_sheet_view(master, sheet: dict, on_change=None):
    system = sheet.get("sistema", dnd5e_sheet.SYSTEM)
    view_class = SYSTEMS.get(system)
    if view_class is None:
        raise ValueError(f"Sistema de ficha desconhecido: {system!r}")
    return view_class(master, sheet, on_change=on_change)


def resources(sheet: dict):
    """Recursos para resumos como a barra lateral do mestre: [(sigla, atual, máximo, cor ou None)].

    Cor None = verde/vermelho conforme o quanto resta.
    """
    if sheet.get("sistema") == ordem_sheet.SYSTEM:
        return [(sigla, sheet.get(key, {}).get("atual", 0), sheet.get(key, {}).get("max", 0),
                 ordem_sheet.RESOURCE_COLORS[key])
                for key, sigla in (("pv", "PV"), ("san", "SAN"))]
    combate = sheet.get("combate", {})
    return [("HP", combate.get("hp_atual", 0), combate.get("hp_max", 0), None)]
