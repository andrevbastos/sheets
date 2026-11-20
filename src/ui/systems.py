"""Escolhe a tela certa para cada sistema de RPG, pela chave "sistema" da ficha.

Para adicionar um sistema novo (ex.: Ordem Paranormal): criar src/ui/<sistema>_sheet.py com uma
classe SheetView(master, sheet, on_change) que tenha set_sheet(sheet), e registrar aqui.
"""
from src.ui import dnd5e_sheet

SYSTEMS = {
    dnd5e_sheet.SYSTEM: dnd5e_sheet.SheetView,
}


def make_sheet_view(master, sheet: dict, on_change=None):
    system = sheet.get("sistema", dnd5e_sheet.SYSTEM)
    view_class = SYSTEMS.get(system)
    if view_class is None:
        raise ValueError(f"Sistema de ficha desconhecido: {system!r}")
    return view_class(master, sheet, on_change=on_change)
