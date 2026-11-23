"""Ficha de ameaça de Ordem Paranormal (só do mestre), no formato das fichas do livro (p. 178-179).

Reaproveita os campos da ficha de agente (src/ui/ordem_sheet.py). Os números são digitados como
no livro, com o dado inteiro ("2d20+10", "2d6+5 corte") e cada teste, perícia e ação tem um botão que rola.
"""
import tkinter as tk

import customtkinter as ctk

from src import ordem
from src.ui import ordem_sheet
from src.ui.common import (ERROR, PANEL, PANEL_DARK, TEXT_DIM, TEXT_FAINT, TEXT_MUTED, WARN, TabBar, dice_icon,
                           small_button, update, update_bar)

TABS = ["Ações", "Habilidades", "Descrição"]
PV_COLOR = ordem_sheet.RESOURCE_COLORS["pv"]


class SheetView(ordem_sheet.SheetView):
    def set_sheet(self, new_sheet: dict):
        if not new_sheet or new_sheet == self.sheet:
            return
        old, self.sheet = self.sheet, new_sheet
        if old.get("cor") != new_sheet.get("cor"):
            self._rebuild()
            return
        if len(old.get("acoes", [])) != len(new_sheet.get("acoes", [])):
            self._populate_actions()
        if len(old.get("habilidades", [])) != len(new_sheet.get("habilidades", [])):
            self._populate_abilities()
        self._sync_fields()
        self._refresh_computed()

    # ================================================================= construção
    def _build(self, active_tab=None):
        self.fields = []
        self.computed = []
        self._built_class = None

        header = self._card(self, fill=tk.X, padx=10, pady=(5, 10))
        self._field(header, ("nome",), width=340, size=20, bold=True, transparent=True, text_color=self.color,
                    placeholder="Nome da ameaça", height=36).pack(side=tk.LEFT, padx=14, pady=8)
        right = ctk.CTkFrame(header, fg_color="transparent")
        right.pack(side=tk.RIGHT, padx=14)
        self._caption(right, "DESCRITORES").pack(side=tk.LEFT, padx=(0, 6))
        self._field(right, ("descritores",), width=170, placeholder="Sangue, Criatura").pack(side=tk.LEFT)
        self._option(right, ("tamanho",), ordem.TAMANHOS, width=100).pack(side=tk.LEFT, padx=(8, 0))
        self._caption(right, "VD").pack(side=tk.LEFT, padx=(16, 6))
        self._field(right, ("vd",), width=56, size=15, bold=True, justify="center").pack(side=tk.LEFT)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        left = self.left_column = ctk.CTkScrollableFrame(body, fg_color="transparent", width=380)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        right_col = ctk.CTkFrame(body, fg_color="transparent")
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self._build_presence(left)
        self._build_life(left)
        self._build_defenses(left)
        self._build_attributes(left)
        self._build_other(left)
        self._build_threat_tabs(right_col, active_tab)

    # ----------------------------------------------------------------- coluna esquerda
    def _build_presence(self, parent):
        card = self._card(parent, None, fill=tk.X, pady=(0, 10))
        self._caption(card, "PRESENÇA PERTURBADORA").pack(anchor=tk.W, padx=12, pady=(8, 2))
        line = ctk.CTkFrame(card, fg_color="transparent")
        line.pack(fill=tk.X, padx=12, pady=(0, 10))
        ctk.CTkLabel(line, text="DT", font=ctk.CTkFont(size=11, weight="bold"), text_color=TEXT_MUTED).pack(side=tk.LEFT)
        self._field(line, ("presenca", "dt"), kind="int", width=40, justify="center", bold=True,
                    clamp=lambda v: max(0, v)).pack(side=tk.LEFT, padx=(4, 8))
        self._field(line, ("presenca", "dano"), width=90, placeholder="2d6 mental").pack(side=tk.LEFT, padx=(0, 4))
        self._roll_button(line, lambda: ordem.dano_request(self.sheet["presenca"]["dano"], "Presença Perturbadora")
                          ).pack(side=tk.LEFT, padx=(0, 8))
        self._field(line, ("presenca", "imune"), width=100, placeholder="NEX 25%+ imune").pack(
            side=tk.LEFT, fill=tk.X, expand=True)

    def _build_life(self, parent):
        card = self._card(parent, None, fill=tk.X, pady=(0, 10))
        frame = ctk.CTkFrame(card, fg_color=PANEL_DARK, corner_radius=8)
        frame.pack(fill=tk.X, padx=12, pady=10)
        top = ctk.CTkFrame(frame, fg_color="transparent")
        top.pack(fill=tk.X, padx=10, pady=(6, 0))
        ctk.CTkLabel(top, text="PV", font=ctk.CTkFont(size=16, weight="bold"), text_color=PV_COLOR).pack(side=tk.LEFT)
        hurt = ctk.CTkLabel(top, text="", font=ctk.CTkFont(size=10, weight="bold"))
        hurt.pack(side=tk.LEFT, padx=8)
        self._computed(lambda: update(hurt, **self._hurt_text()))
        vals = ctk.CTkFrame(top, fg_color="transparent")
        vals.pack(side=tk.RIGHT)
        self._field(vals, ("pv", "atual"), kind="int", width=52, size=16, bold=True, justify="center",
                    clamp=lambda v: max(0, min(v, self.sheet["pv"]["max"]))).pack(side=tk.LEFT)
        ctk.CTkLabel(vals, text="/", font=ctk.CTkFont(size=16), text_color=TEXT_MUTED).pack(side=tk.LEFT, padx=4)
        self._field(vals, ("pv", "max"), kind="int", width=52, size=16, justify="center",
                    clamp=lambda v: max(0, v)).pack(side=tk.LEFT)

        bar = ctk.CTkProgressBar(frame, fg_color="#2b2b2b", progress_color=PV_COLOR, height=8)
        bar.pack(fill=tk.X, padx=10, pady=6)
        self._computed(lambda: update_bar(bar, self.sheet["pv"]["atual"] / max(1, self.sheet["pv"]["max"])))
        buttons = ctk.CTkFrame(frame, fg_color="transparent")
        buttons.pack(fill=tk.X, padx=10, pady=(0, 8))
        for delta in (-10, -5, -1, 1, 5, 10):
            small_button(buttons, f"+{delta}" if delta > 0 else str(delta),
                         lambda d=delta: self._adjust("pv", d)).pack(side=tk.LEFT, padx=3)

    def _hurt_text(self):
        pv, limite = self.sheet["pv"], ordem.machucado(self.sheet)
        if pv["max"] and pv["atual"] == 0:
            return {"text": "DERROTADA", "text_color": ERROR}
        if pv["max"] and pv["atual"] <= limite:
            return {"text": f"MACHUCADA (≤ {limite})", "text_color": WARN}
        return {"text": f"machucada em {limite}", "text_color": TEXT_FAINT}

    def _build_defenses(self, parent):
        card = self._card(parent, None, fill=tk.X, pady=(0, 10))
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill=tk.X, padx=12, pady=(10, 4))
        shield = ctk.CTkFrame(top, fg_color=PANEL_DARK, corner_radius=8, width=74, height=64)
        shield.pack(side=tk.LEFT, padx=(0, 10))
        shield.pack_propagate(False)
        self._caption(shield, "DEFESA").pack(pady=(5, 0))
        self._field(shield, ("defesa",), kind="int", width=50, size=20, bold=True, justify="center",
                    transparent=True, height=30).pack()

        grid = ctk.CTkFrame(top, fg_color="transparent")
        grid.pack(side=tk.LEFT, fill=tk.X, expand=True)
        for r, (key, nome, _attr) in enumerate(ordem.AMEACA_TESTES):
            row, col = divmod(r, 2) if r < 4 else (2, 0)
            cell = ctk.CTkFrame(grid, fg_color="transparent")
            cell.grid(row=row, column=col, sticky="w", padx=(0, 6), pady=1)
            self._caption(cell, nome[:4].upper() + ".").pack(side=tk.LEFT)
            self._field(cell, ("testes", key), width=58, justify="center", height=22).pack(side=tk.LEFT, padx=3)
            self._roll_button(cell, lambda k=key: ordem.ameaca_pericia_request(self.sheet, k)).pack(side=tk.LEFT)

        lines = ctk.CTkFrame(card, fg_color="transparent")
        lines.pack(fill=tk.X, padx=12, pady=(4, 10))
        lines.grid_columnconfigure(1, weight=1)
        for r, (label, key, hint) in enumerate((
                ("SENTIDOS", "sentidos", "ex.: percepção às cegas"),
                ("RESISTÊNCIAS", "resistencias", "ex.: balístico e impacto 5, Sangue 10"),
                ("VULNERÁVEL", "vulnerabilidades", "ex.: Morte"))):
            self._caption(lines, label).grid(row=r, column=0, sticky="nw", pady=(6, 2), padx=(0, 8))
            self._textbox(lines, (key,), framed=True, placeholder=hint).grid(row=r, column=1, sticky="ew", pady=2)

    def _build_other(self, parent):
        card = self._card(parent, None, fill=tk.X, pady=(0, 10))
        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(fill=tk.X, padx=12, pady=(10, 2))
        grid.grid_columnconfigure(1, weight=1)
        self._caption(grid, "PERÍCIAS").grid(row=0, column=0, sticky="nw", pady=(6, 2), padx=(0, 8))
        self._textbox(grid, ("pericias",), framed=True, placeholder="ex.: Furtividade 2d20+13, Luta 3d20+10").grid(
            row=0, column=1, sticky="ew", pady=2)
        self._caption(grid, "DESLOCAMENTO").grid(row=1, column=0, sticky="w", pady=2, padx=(0, 8))
        self._field(grid, ("deslocamento",), width=80).grid(row=1, column=1, sticky="w", pady=2)

        chips = ctk.CTkFrame(card, fg_color="transparent")
        chips.pack(fill=tk.X, padx=12, pady=(2, 10))
        state = {"shown": None}

        def refresh():
            if not chips.winfo_exists():
                raise tk.TclError("ficha refeita")
            pericias = ordem.pericias_ameaca(self.sheet)
            if pericias == state["shown"]:
                return
            state["shown"] = pericias
            for child in chips.winfo_children():
                child.destroy()
            for nome, n_dados, bonus in pericias:
                req = ordem.teste_request(n_dados, bonus, nome)
                button = small_button(chips, f"{nome} {ordem.fmt_teste(n_dados, bonus)}", None, width=40,
                                      height=22, image=dice_icon(dim=self.on_roll is None), compound="left")
                self._rollable(button, lambda r=req: r)
                button.pack(side=tk.LEFT, padx=(0, 4), pady=2)
                if self.on_roll is None:
                    button.configure(state="disabled")

        self._computed(refresh)

    # ----------------------------------------------------------------- abas
    def _build_threat_tabs(self, parent, active_tab):
        container = self._card(parent, None, fill=tk.BOTH, expand=True)
        content = ctk.CTkFrame(container, fg_color="transparent")
        self.tabs = TabBar(container, content, self._get_color, main=True)
        self.tabs.header.pack(fill=tk.X, side=tk.TOP)
        content.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        views = {name: ctk.CTkFrame(content, fg_color="transparent") for name in TABS}
        for name in TABS:
            self.tabs.add(name, views[name])
        self.actions_view = views["Ações"]
        self._populate_actions()
        self.abilities_view = views["Habilidades"]
        self._populate_abilities()
        self._build_description(views["Descrição"])
        self.tabs.switch(active_tab if active_tab in views else None)

    ACTION_ADD_COLS = [(150, True), (110, False), (110, False)]

    def _populate_actions(self):
        view = self.actions_view
        for child in view.winfo_children():
            child.destroy()
        path = ("acoes",)

        def add(es):
            nome, teste, dano = (e.get().strip() for e in es)
            self._append(path, {"tipo": "Padrão", "nome": nome, "teste": teste, "dano": dano, "descricao": ""},
                         es, self._populate_actions)

        scroll = self._list_section(view, self.ACTION_ADD_COLS, ("Ação ou ataque", "Teste (3d20+10)", "Dano"), add)
        for idx in range(len(self.sheet["acoes"])):
            base = path + (idx,)
            row = ctk.CTkFrame(scroll, fg_color=PANEL)
            row.pack(fill=tk.X, pady=3, padx=4)
            line = ctk.CTkFrame(row, fg_color="transparent")
            line.pack(fill=tk.X)
            small_button(line, "X", lambda i=idx: self._remove(path, i, self._populate_actions), width=24,
                         danger=True, height=20).pack(side=tk.RIGHT, padx=8)
            self._option(line, base + ("tipo",), ordem.TIPOS_ACAO, width=96).pack(side=tk.LEFT, padx=(6, 3), pady=3)
            # nome em branco: as cores das ameaças costumam ser escuras demais para ler
            self._field(line, base + ("nome",), width=80, transparent=True, bold=True, size=12).pack(
                side=tk.LEFT, padx=3, fill=tk.X, expand=True)

            # segunda linha: [d20 Teste] campo   [d20 Dano] campo (na primeira não cabe com o nome)
            rolls_line = ctk.CTkFrame(row, fg_color="transparent")
            rolls_line.pack(fill=tk.X, padx=(6, 0))
            rolls = self._attack_rolls(path)
            for key, label, width in (("teste", "Teste", 120), ("dano", "Dano", 120)):
                self._roll_button(rolls_line, lambda f=rolls[key], i=idx: f(i), text=label, width=64).pack(
                    side=tk.LEFT, padx=(4, 0))
                self._field(rolls_line, base + (key,), width=width, height=22, placeholder="—").pack(
                    side=tk.LEFT, padx=(4, 12))
            self._textbox(row, base + ("descricao",), auto_height=True, text_color=TEXT_DIM,
                          placeholder="Alcance, efeito ao acertar, resistência...").pack(fill=tk.X, padx=6,
                                                                                          pady=(0, 6))

    HABILIDADE_COLS = [(200, True), (200, True)]

    def _populate_abilities(self):
        view = self.abilities_view
        for child in view.winfo_children():
            child.destroy()
        keys = ("nome", "descricao")
        scroll = self._list_section(
            view, self.HABILIDADE_COLS, ("Habilidade (sempre ativa)", "Descrição"),
            lambda es: self._append(("habilidades",), {k: e.get().strip() for k, e in zip(keys, es)}, es,
                                    self._populate_abilities))
        self._list_rows(scroll, ("habilidades",), self.sheet["habilidades"], self.HABILIDADE_COLS, keys,
                        lambda i: self._remove(("habilidades",), i, self._populate_abilities),
                        wrap_key="descricao", placeholder="O que a habilidade faz...")

    def _adjust(self, key, delta):
        res = self.sheet[key]
        value = max(0, min(res["atual"] + delta, res["max"]))
        if value != res["atual"]:
            res["atual"] = value
            self._changed()

