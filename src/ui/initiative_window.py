"""Janela de iniciativa do mestre: ordem dos turnos, rodada atual e rolagem de iniciativa.

Quem entra: todas as fichas abertas na barra lateral (agentes e ameaças) e nomes avulsos
(ex.: "Filhote 2", um civil sem ficha). A rolagem passa pelo servidor, como qualquer outra:
os jogadores veem a iniciativa dos agentes; a das ameaças pode ser privada.
"""
import tkinter as tk
from dataclasses import dataclass

import customtkinter as ctk

from src.sheet_io import to_int
from src.ui.common import (BG, BORDER, BUTTON, BUTTON_HOVER, INPUT, PANEL, PANEL_DARK, TEXT, TEXT_DIM, TEXT_FAINT,
                           TEXT_MUTED, TITLE_FONT, WARN, dice_icon, small_button, update, update_bar)



@dataclass
class Combatant:
    key: str                  # chave da barra lateral, ou "extra:<n>" para nomes avulsos
    nome: str
    valor: int | None = None  # resultado da iniciativa
    bonus: int = 0            # desempate: maior bônus age antes
    threat: bool = False


class InitiativeWindow(ctk.CTkToplevel):
    """`get_entries()` -> [(chave, nome, ficha, é_ameaça)]; `roll(pedido, privada)` -> resultado ou None;
    `request_for(ficha)` -> pedido de iniciativa ou None; `on_select(chave)` mostra a ficha na tela do mestre;
    `resources(ficha)` -> [(sigla, atual, máximo, cor)] para a barrinha de PV."""

    def __init__(self, master, get_entries, roll, request_for, on_select, resources):
        super().__init__(master)
        self.get_entries, self.roll_fn, self.request_for = get_entries, roll, request_for
        self.on_select, self.resources = on_select, resources
        self.title("Iniciativa")
        self.geometry("400x560")
        self.minsize(360, 420)
        self.configure(fg_color=BG)
        self.protocol("WM_DELETE_WINDOW", self.withdraw)  # fechar só esconde; a ordem continua
        self.combatants: list[Combatant] = []
        self.turn = 0
        self.round = 1
        self._extra_count = 0
        self._rendered_shape = None
        self._bars = {}
        self._entries = {}
        self._build()
        self.refresh()

    def show(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    # ================================================================= interface
    def _build(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill=tk.X, padx=14, pady=(12, 6))
        ctk.CTkLabel(top, text="INICIATIVA", font=ctk.CTkFont(family=TITLE_FONT, size=16, weight="bold"),
                     text_color=TEXT).pack(side=tk.LEFT)
        self.lbl_round = ctk.CTkLabel(top, text="", font=ctk.CTkFont(size=13, weight="bold"), text_color=WARN)
        self.lbl_round.pack(side=tk.RIGHT)

        actions = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=10)
        actions.pack(fill=tk.X, padx=14)
        row = ctk.CTkFrame(actions, fg_color="transparent")
        row.pack(fill=tk.X, padx=8, pady=(8, 4))
        for text, command in (("Rolar todos", self.roll_all), ("Próximo turno", self.next_turn),
                              ("Recomeçar", self.reset)):
            ctk.CTkButton(row, text=text, height=28, width=10, fg_color=BUTTON, hover_color=BUTTON_HOVER,
                          font=ctk.CTkFont(size=11, weight="bold"), command=command, compound="left",
                          image=dice_icon() if command == self.roll_all else None).pack(
                side=tk.LEFT, fill=tk.X, expand=True, padx=3)
        self.private = ctk.CTkCheckBox(actions, text="Ameaças rolam em privado", font=ctk.CTkFont(size=11),
                                       checkbox_width=16, checkbox_height=16)
        self.private.select()
        self.private.pack(anchor=tk.W, padx=12, pady=(2, 8))

        self.list = ctk.CTkScrollableFrame(self, fg_color=PANEL_DARK)
        self.list.pack(fill=tk.BOTH, expand=True, padx=14, pady=8)

        add = ctk.CTkFrame(self, fg_color="transparent")
        add.pack(fill=tk.X, padx=14, pady=(0, 12))
        self.extra_name = ctk.CTkEntry(add, placeholder_text="Outro (ex.: Filhote 2)", height=26, fg_color=INPUT,
                                       border_color=BORDER, font=ctk.CTkFont(size=11))
        self.extra_name.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.extra_value = ctk.CTkEntry(add, placeholder_text="Inic.", width=50, height=26, justify="center",
                                        fg_color=INPUT, border_color=BORDER, font=ctk.CTkFont(size=11))
        self.extra_value.pack(side=tk.LEFT, padx=4)
        ctk.CTkButton(add, text="Adicionar", width=80, height=26, fg_color=BUTTON, hover_color=BUTTON_HOVER,
                      font=ctk.CTkFont(size=11), command=self.add_extra).pack(side=tk.LEFT)
        for entry in (self.extra_name, self.extra_value):
            entry.bind("<Return>", lambda *_: self.add_extra())

    # ================================================================= dados
    def refresh(self):
        """Acompanha a barra lateral: fichas novas entram (sem iniciativa), fichas fechadas saem."""
        entries = {key: (nome, sheet, threat) for key, nome, sheet, threat in self.get_entries()}
        current = self.combatants[self.turn] if self.combatants else None
        kept = []
        for c in self.combatants:
            if c.key.startswith("extra:"):
                kept.append(c)
            elif c.key in entries:
                c.nome, c.threat = entries[c.key][0], entries[c.key][2]
                kept.append(c)
        known = {c.key for c in kept}
        kept += [Combatant(key, nome, threat=threat) for key, (nome, _s, threat) in entries.items() if key not in known]
        self.combatants = kept
        self.turn = self.combatants.index(current) if current in self.combatants else 0
        self._entries = entries
        if self._shape() == self._rendered_shape:
            self._update_bars()  # só o PV mudou: atualiza as barras sem refazer as linhas
        else:
            self._render()

    def _shape(self):
        return [(c.key, c.nome, c.threat, c.valor, self._entries.get(c.key, (None, None))[1] is not None)
                for c in self.combatants] + [self.turn, self.round]

    def _update_bars(self):
        for key, (bar, label) in self._bars.items():
            entry = self._entries.get(key)
            if entry:
                for sigla, atual, maximo, _color in self.resources(entry[1])[:1]:
                    update(label, text=f"{sigla} {atual}/{maximo}")
                    update_bar(bar, atual / max(1, maximo))

    def _sort(self):
        current = self.combatants[self.turn] if self.combatants else None
        # sem iniciativa vai para o fim; empate: maior bônus, depois agentes antes de ameaças
        self.combatants.sort(key=lambda c: (c.valor is None, -(c.valor or 0), -c.bonus, c.threat))
        self.turn = self.combatants.index(current) if current else 0

    def roll_one(self, combatant: Combatant, render=True):
        entry = self._entries.get(combatant.key)
        req = self.request_for(entry[1]) if entry else None
        if req is None:
            return
        private = combatant.threat and bool(self.private.get())
        result = self.roll_fn(req, private)
        if result:
            combatant.valor, combatant.bonus = result["total"], req.get("bonus", 0)
        if render:
            self._sort()
            self._render()

    def roll_all(self):
        for c in self.combatants:
            self.roll_one(c, render=False)
        self._sort()
        self.turn, self.round = 0, 1
        self._render()

    def next_turn(self):
        if not self.combatants:
            return
        self.turn += 1
        if self.turn >= len(self.combatants):
            self.turn, self.round = 0, self.round + 1
        self._render()

    def reset(self):
        for c in self.combatants:
            c.valor, c.bonus = None, 0
        self.combatants = [c for c in self.combatants if not c.key.startswith("extra:")]
        self.turn, self.round = 0, 1
        self._render()

    def add_extra(self):
        nome = self.extra_name.get().strip()
        if not nome:
            return
        self._extra_count += 1
        valor = self.extra_value.get().strip()
        self.combatants.append(Combatant(f"extra:{self._extra_count}", nome, to_int(valor, 0) if valor else None,
                                         threat=True))
        self.extra_name.delete(0, tk.END)
        self.extra_value.delete(0, tk.END)
        self._sort()
        self._render()

    def _set_value(self, combatant, text):
        combatant.valor = to_int(text, 0) if text.strip() else None
        self._sort()
        self._render()

    def _remove(self, combatant):
        if combatant in self.combatants:
            idx = self.combatants.index(combatant)
            self.combatants.remove(combatant)
            if idx < self.turn:
                self.turn -= 1
            if self.turn >= len(self.combatants):
                self.turn = 0
            self._render()

    # ================================================================= desenho
    def _render(self):
        update(self.lbl_round, text=f"Rodada {self.round}")
        self._rendered_shape = self._shape()
        self._bars = {}
        for child in self.list.winfo_children():
            child.destroy()
        if not self.combatants:
            ctk.CTkLabel(self.list, text="Abra fichas na barra lateral ou adicione um nome abaixo.",
                         font=ctk.CTkFont(size=11, slant="italic"), text_color=TEXT_FAINT,
                         wraplength=300).pack(pady=20)
            return
        for idx, c in enumerate(self.combatants):
            self._row(idx, c)

    def _row(self, idx, c: Combatant):
        active = idx == self.turn
        entry = self._entries.get(c.key)
        sheet = entry[1] if entry else None
        color = sheet.get("cor", TEXT) if sheet else TEXT_DIM
        row = ctk.CTkFrame(self.list, fg_color=PANEL if active else "transparent", corner_radius=6,
                           border_width=2 if active else 0, border_color=WARN)
        row.pack(fill=tk.X, pady=2, padx=2)
        ctk.CTkLabel(row, text="▶" if active else "", width=14, text_color=WARN,
                     font=ctk.CTkFont(size=12)).pack(side=tk.LEFT, padx=(6, 0))

        value = ctk.CTkEntry(row, width=40, height=24, justify="center", fg_color=INPUT, border_color=BORDER,
                             font=ctk.CTkFont(size=13, weight="bold"))
        if c.valor is not None:
            value.insert(0, str(c.valor))
        value.pack(side=tk.LEFT, padx=4, pady=4)
        def save(*_):
            text = value.get().strip()
            if text != ("" if c.valor is None else str(c.valor)):
                self.after_idle(lambda: self._set_value(c, text))  # redesenha fora do evento do próprio campo

        value.bind("<Return>", save)
        value.bind("<FocusOut>", save)

        # botões da direita antes do meio, que se estica e ocuparia o espaço deles
        small_button(row, "X", lambda: self._remove(c), width=22, danger=True, height=20).pack(side=tk.RIGHT, padx=6)
        if sheet and self.request_for(sheet):
            small_button(row, "", lambda: self.roll_one(c), width=26, height=22, image=dice_icon()).pack(
                side=tk.RIGHT)

        middle = ctk.CTkFrame(row, fg_color="transparent")
        middle.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        name = ctk.CTkLabel(middle, text=c.nome + ("  (ameaça)" if c.threat and sheet else ""), anchor="w",
                            font=ctk.CTkFont(size=12, weight="bold"), text_color=color, height=18,
                            cursor="hand2" if sheet else "")
        name.pack(fill=tk.X)
        if sheet:
            name.bind("<Button-1>", lambda *_: self.on_select(c.key))
            for sigla, atual, maximo, res_color in self.resources(sheet)[:1]:
                bar_row = ctk.CTkFrame(middle, fg_color="transparent")
                bar_row.pack(fill=tk.X)
                label = ctk.CTkLabel(bar_row, text=f"{sigla} {atual}/{maximo}", font=ctk.CTkFont(size=9),
                                     height=12, text_color=TEXT_MUTED)
                label.pack(side=tk.RIGHT, padx=(6, 0))
                bar = ctk.CTkProgressBar(bar_row, height=5, fg_color=BUTTON, progress_color=res_color or "#2ecc71")
                update_bar(bar, atual / max(1, maximo))
                bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
                self._bars[c.key] = (bar, label)
