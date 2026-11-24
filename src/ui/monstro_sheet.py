"""Ficha de monstro de D&D 5e (só do mestre), no formato do bloco de estatísticas dos livros.

Reaproveita a ficha de personagem (src/ui/dnd5e_sheet.py): modificadores, testes de resistência,
iniciativa, ataques com "FOR"/"DES" e dano/cura. O ND define a proficiência e o XP (src/dnd.py).
Os testes de resistência ficam junto dos atributos para economizar espaço.
"""
import tkinter as tk

import customtkinter as ctk

from src import dnd
from src.ui import dnd5e_sheet
from src.ui.common import (BUTTON, ERROR, OK, PANEL, PANEL_DARK, TEXT, TEXT_DIM, TEXT_FAINT, TEXT_MUTED, TabBar,
                           dice_icon, fmt_bonus, small_button, update, update_bar)

TABS = ["Ações", "Habilidades", "Descrição"]


class SheetView(dnd5e_sheet.SheetView):
    DEFAULT_COLOR = "#a33b3b"

    def _needs_rebuild(self):
        return False

    def set_sheet(self, new_sheet: dict):
        if not new_sheet or new_sheet == self.sheet:
            return
        old, self.sheet = self.sheet, new_sheet
        if old.get("cor") != new_sheet.get("cor"):
            self._rebuild()
            return
        if [a["tipo"] for a in old.get("acoes", [])] != [a["tipo"] for a in new_sheet.get("acoes", [])]:
            self._populate_actions()
        if len(old.get("habilidades", [])) != len(new_sheet.get("habilidades", [])):
            self._populate_abilities()
        self._sync_fields()
        self._refresh_computed()

    # ================================================================= construção
    def _build(self, active_tab=None):
        self.fields = []
        self.computed = []

        header = self._card(self, fill=tk.X, padx=10, pady=(5, 10))
        top = ctk.CTkFrame(header, fg_color="transparent")
        top.pack(fill=tk.X, padx=14, pady=(8, 0))
        self._field(top, ("nome",), width=300, size=20, bold=True, transparent=True, text_color=self.color,
                    placeholder="Nome do monstro", height=36).pack(side=tk.LEFT)
        right = ctk.CTkFrame(top, fg_color="transparent")
        right.pack(side=tk.RIGHT)
        self._caption(right, "ND").pack(side=tk.LEFT, padx=(0, 4))
        self._option(right, ("nd",), dnd.NDS, width=62).pack(side=tk.LEFT)
        info = ctk.CTkLabel(right, text="", font=ctk.CTkFont(size=11), text_color=TEXT_DIM)
        info.pack(side=tk.LEFT, padx=(10, 0))
        self._computed(lambda: update(info, text=f"{self.sheet['xp']:,} XP  ·  proficiência "
                                                 f"{fmt_bonus(dnd.prof(self.sheet))}".replace(",", ".")))
        line = ctk.CTkFrame(header, fg_color="transparent")
        line.pack(fill=tk.X, padx=14, pady=(2, 8))
        self._option(line, ("tamanho",), dnd.TAMANHOS, width=92).pack(side=tk.LEFT)
        self._field(line, ("criatura",), width=200, placeholder="Humanoide (goblinoide)").pack(
            side=tk.LEFT, padx=6, fill=tk.X, expand=True)
        self._field(line, ("tendencia",), width=150, placeholder="Neutro e Mau").pack(side=tk.LEFT)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        left = ctk.CTkScrollableFrame(body, fg_color="transparent", width=380)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        right_col = ctk.CTkFrame(body, fg_color="transparent")
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self._build_monster_combat(left)
        self._build_monster_attributes(left)
        self._build_details(left)
        self._build_monster_tabs(right_col, active_tab)

    # ----------------------------------------------------------------- coluna esquerda
    def _build_monster_combat(self, parent):
        card = self._card(parent, None, fill=tk.X, pady=(0, 10))
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill=tk.X, padx=12, pady=(10, 4))
        for idx in range(3):
            top.grid_columnconfigure(idx, weight=1, uniform="combate")

        def box(idx, label):
            frame = ctk.CTkFrame(top, fg_color=PANEL_DARK, corner_radius=6)
            frame.grid(row=0, column=idx, padx=2, sticky="nsew")
            self._caption(frame, label).pack(pady=(5, 0))
            return frame

        ca = box(0, "CA")
        self._field(ca, ("combate", "ca"), kind="int", width=44, size=18, bold=True, justify="center",
                    transparent=True).pack()
        self._field(ca, ("combate", "ca_descricao"), width=60, height=20, size=9, justify="center",
                    transparent=True, placeholder="armadura natural").pack(fill=tk.X, padx=2, pady=(0, 4))
        ini = box(1, "INICIATIVA")
        self._bonus_button(ini, lambda: dnd.iniciativa_request(self.sheet, "Iniciativa"),
                           lambda: fmt_bonus(dnd.iniciativa(self.sheet)), width=56, size=14).pack(pady=2)
        outros = ctk.CTkFrame(ini, fg_color="transparent")
        outros.pack(pady=(0, 6))
        ctk.CTkLabel(outros, text="outros", font=ctk.CTkFont(size=9), text_color=TEXT_FAINT).pack(side=tk.LEFT, padx=2)
        self._field(outros, ("combate", "iniciativa_outros"), kind="int", width=28, height=20,
                    justify="center").pack(side=tk.LEFT)
        self._field(box(2, "DESLOC."), ("combate", "deslocamento"), width=100, size=12, bold=True,
                    justify="center", transparent=True, placeholder="9 m, voo 18 m").pack(pady=(4, 6), padx=4)

        frame = ctk.CTkFrame(card, fg_color=PANEL_DARK, corner_radius=8)
        frame.pack(fill=tk.X, padx=12, pady=(6, 12))
        head = ctk.CTkFrame(frame, fg_color="transparent")
        head.pack(fill=tk.X, padx=10, pady=(6, 0))
        ctk.CTkLabel(head, text="PV", font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXT).pack(side=tk.LEFT)
        state = ctk.CTkLabel(head, text="", font=ctk.CTkFont(size=10, weight="bold"))
        state.pack(side=tk.LEFT, padx=8)
        self._computed(lambda: update(state, **self._state_text()))
        vals = ctk.CTkFrame(head, fg_color="transparent")
        vals.pack(side=tk.RIGHT)
        self._caption(vals, "TEMP").pack(side=tk.LEFT, padx=(0, 4))
        self._field(vals, ("combate", "hp_temp"), kind="int", width=32, justify="center",
                    clamp=lambda v: max(0, v)).pack(side=tk.LEFT, padx=(0, 10))
        self._field(vals, ("combate", "hp_atual"), kind="int", width=48, size=16, bold=True, justify="center",
                    clamp=lambda v: max(0, min(v, self.sheet["combate"]["hp_max"]))).pack(side=tk.LEFT)
        ctk.CTkLabel(vals, text="/", font=ctk.CTkFont(size=16), text_color=TEXT_MUTED).pack(side=tk.LEFT, padx=4)
        self._field(vals, ("combate", "hp_max"), kind="int", width=48, size=16, justify="center",
                    clamp=lambda v: max(0, v)).pack(side=tk.LEFT)
        bar = ctk.CTkProgressBar(frame, fg_color=BUTTON, height=8)
        bar.pack(fill=tk.X, padx=10, pady=6)

        def show_hp():
            c = self.sheet["combate"]
            ratio = c["hp_atual"] / max(1, c["hp_max"])
            update_bar(bar, ratio)
            update(bar, progress_color=OK if ratio > 0.5 else ERROR)  # vermelho a partir da metade (sangrando)
        self._computed(show_hp)

        buttons = ctk.CTkFrame(frame, fg_color="transparent")
        buttons.pack(fill=tk.X, padx=10, pady=(0, 6))
        for delta in (-5, -1, 1, 5):
            small_button(buttons, f"+{delta}" if delta > 0 else str(delta),
                         lambda d=delta: self._hp_change(d)).pack(side=tk.LEFT, padx=2)
        amount = ctk.CTkEntry(buttons, width=40, height=22, justify="center", placeholder_text="valor",
                              font=ctk.CTkFont(size=10))
        amount.pack(side=tk.LEFT, padx=(10, 2))
        for text, sign in (("Dano", -1), ("Cura", 1)):
            small_button(buttons, text, lambda s=sign: self._hp_from_entry(amount, s), width=44).pack(
                side=tk.LEFT, padx=2)
        amount.bind("<Return>", lambda *_: self._hp_from_entry(amount, -1))

        # fórmula dos PV: "Média" preenche os PV como nos livros; o dado rola para quem prefere PV rolados
        formula = ctk.CTkFrame(frame, fg_color="transparent")
        formula.pack(fill=tk.X, padx=10, pady=(0, 8))
        self._caption(formula, "FÓRMULA").pack(side=tk.LEFT)
        self._field(formula, ("combate", "formula_pv"), width=90, height=22, placeholder="2d6+2").pack(
            side=tk.LEFT, padx=6)
        self._roll_button(formula, lambda: dnd.dano_request(self.sheet, self.sheet["combate"]["formula_pv"],
                                                            "Pontos de vida")).pack(side=tk.LEFT)
        average = small_button(formula, "Usar média", self._use_average, width=78)
        average.pack(side=tk.LEFT, padx=6)
        self._computed(lambda: update(average, text=self._average_text()))

    def _state_text(self):
        c = self.sheet["combate"]
        if c["hp_max"] and c["hp_atual"] == 0:
            return {"text": "DERROTADO", "text_color": ERROR}
        if c["hp_max"] and c["hp_atual"] <= c["hp_max"] // 2:
            return {"text": "SANGRANDO", "text_color": ERROR}
        return {"text": "", "text_color": TEXT_FAINT}

    def _average_text(self):
        media = dnd.pv_media(self.sheet["combate"]["formula_pv"])
        return "Usar média" if media is None else f"Média {media}"

    def _use_average(self):
        media = dnd.pv_media(self.sheet["combate"]["formula_pv"])
        if media is None:
            return
        c = self.sheet["combate"]
        c["hp_max"] = c["hp_atual"] = media
        self._changed()

    def _build_monster_attributes(self, parent):
        """Cada atributo: modificador (rola o teste), valor e, embaixo, a resistência com a bolinha de proficiência."""
        card = self._card(parent, "ATRIBUTOS E RESISTÊNCIAS", fill=tk.X, pady=(0, 10))
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill=tk.X, padx=8, pady=(0, 4))
        for idx, (attr, sigla, nome) in enumerate(dnd.ATRIBUTOS):
            row.grid_columnconfigure(idx, weight=1)
            box = ctk.CTkFrame(row, fg_color=PANEL_DARK, corner_radius=6)
            box.grid(row=0, column=idx, padx=2, sticky="nsew")
            self._caption(box, sigla).pack(pady=(5, 0))
            self._bonus_button(box, lambda a=attr: dnd.atributo_request(self.sheet, a),
                               lambda a=attr: fmt_bonus(dnd.mod(self.sheet, a)), width=50, size=15).pack(pady=2)
            self._field(box, ("atributos", attr, "valor"), kind="int", width=38, height=22, justify="center",
                        clamp=lambda v: max(1, min(v, 30))).pack(pady=(0, 4))
            path = ("resistencia", attr, "proficiente")
            dot = ctk.CTkButton(box, text="", width=50, height=16, fg_color="transparent", hover_color=PANEL,
                                font=ctk.CTkFont(size=9, weight="bold"),
                                command=lambda p=path: self._commit(p, not self._get(p)))
            dot.pack()
            self._computed(lambda d=dot, p=path: update(d, text=("●" if self._get(p) else "○") + " RES",
                                                         text_color=self.color if self._get(p) else TEXT_MUTED))
            self._bonus_button(box, lambda a=attr: dnd.resistencia_request(self.sheet, a),
                               lambda a=attr: fmt_bonus(dnd.bonus_resistencia(self.sheet, a)),
                               color_fn=lambda a=attr: TEXT if self.sheet["resistencia"][a]["proficiente"] else TEXT_DIM,
                               width=50, size=11).pack(pady=(0, 6))
        ctk.CTkLabel(card, text="RES = teste de resistência. A bolinha soma a proficiência do ND.",
                     font=ctk.CTkFont(size=9, slant="italic"), text_color=TEXT_FAINT).pack(pady=(0, 8))

    def _build_details(self, parent):
        card = self._card(parent, None, fill=tk.X, pady=(0, 10))
        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(fill=tk.X, padx=12, pady=(10, 2))
        grid.grid_columnconfigure(1, weight=1)
        self._caption(grid, "PERÍCIAS").grid(row=0, column=0, sticky="nw", pady=(6, 2), padx=(0, 8))
        self._textbox(grid, ("pericias",), framed=True, placeholder="ex.: Furtividade +6, Percepção").grid(
            row=0, column=1, sticky="ew", pady=2)
        chips = ctk.CTkFrame(grid, fg_color="transparent")
        chips.grid(row=1, column=1, sticky="ew")
        self._skill_chips(chips)

        rows = (("SENTIDOS", "sentidos", "ex.: visão no escuro 18 m"),
                ("IDIOMAS", "idiomas", "ex.: Comum, Goblin"),
                ("VULNERÁVEL", "vulnerabilidades_dano", "ex.: fogo"),
                ("RESISTÊNCIAS", "resistencias_dano", "ex.: frio; contundente de ataques não mágicos"),
                ("IMUNE (DANO)", "imunidades_dano", "ex.: veneno"),
                ("IMUNE (COND.)", "imunidades_condicao", "ex.: envenenado, enfeitiçado"))
        for r, (label, key, hint) in enumerate(rows, start=2):
            self._caption(grid, label).grid(row=r, column=0, sticky="nw", pady=(6, 2), padx=(0, 8))
            self._textbox(grid, (key,), framed=True, placeholder=hint).grid(row=r, column=1, sticky="ew", pady=2)
        passive = ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=10), text_color=TEXT_MUTED)
        passive.pack(anchor=tk.E, padx=12, pady=(0, 10))
        self._computed(lambda: update(passive, text=f"Percepção passiva {self.sheet['percepcao_passiva']}"))

    def _skill_chips(self, chips):
        state = {"shown": None}

        def refresh():
            if not chips.winfo_exists():
                raise tk.TclError("ficha refeita")
            pericias = dnd.pericias_monstro(self.sheet)
            if pericias == state["shown"]:
                return
            state["shown"] = pericias
            for child in chips.winfo_children():
                child.destroy()
            for nome, bonus in pericias:
                button = small_button(chips, f"{nome} {fmt_bonus(bonus)}", None, width=40, height=22,
                                      image=dice_icon(dim=self.on_roll is None), compound="left")
                self._rollable(button, lambda n=nome, b=bonus: dnd.teste_request(b, n))
                button.pack(side=tk.LEFT, padx=(0, 4), pady=2)
                if self.on_roll is None:
                    button.configure(state="disabled")

        self._computed(refresh)

    # ----------------------------------------------------------------- abas
    def _build_monster_tabs(self, parent, active_tab):
        container = self._card(parent, None, fill=tk.BOTH, expand=True)
        content = ctk.CTkFrame(container, fg_color="transparent")
        self.tabs = TabBar(container, content, self._get_color, main=True)
        self.tabs.header.pack(fill=tk.X, side=tk.TOP)
        content.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        views = {name: ctk.CTkFrame(content, fg_color="transparent") for name in TABS}
        for name in TABS:
            self.tabs.add(name, views[name])
        self._build_legendary(views["Ações"])
        self.actions_view = ctk.CTkFrame(views["Ações"], fg_color="transparent")
        self.actions_view.pack(fill=tk.BOTH, expand=True)
        self._populate_actions()
        self.abilities_view = views["Habilidades"]
        self._populate_abilities()
        self._textbox(views["Descrição"], ("descricao",),
                      placeholder="Aparência, comportamento, táticas, onde vive...").pack(fill=tk.BOTH, expand=True)
        self.tabs.switch(active_tab if active_tab in views else None)

    def _build_legendary(self, view):
        """Ações lendárias por rodada (contador). O máximo 0 deixa a linha discreta."""
        line = ctk.CTkFrame(view, fg_color=PANEL_DARK, corner_radius=6)
        line.pack(fill=tk.X, pady=(0, 8))
        self._caption(line, "AÇÕES LENDÁRIAS").pack(side=tk.LEFT, padx=(10, 8), pady=4)
        small_button(line, "−", lambda: self._legendary_step(-1), width=20, height=20).pack(side=tk.LEFT, padx=1)
        self._field(line, ("lendarias", "atual"), kind="int", width=28, height=20, bold=True, justify="center",
                    clamp=lambda v: max(0, min(v, self.sheet["lendarias"]["max"]))).pack(side=tk.LEFT)
        ctk.CTkLabel(line, text="/", text_color=TEXT_MUTED, width=8).pack(side=tk.LEFT)
        self._field(line, ("lendarias", "max"), kind="int", width=28, height=20, justify="center",
                    transparent=True, clamp=lambda v: max(0, v)).pack(side=tk.LEFT)
        small_button(line, "+", lambda: self._legendary_step(1), width=20, height=20).pack(side=tk.LEFT, padx=1)
        small_button(line, "Recuperar", self._legendary_reset, width=70, height=20).pack(side=tk.LEFT, padx=8)
        ctk.CTkLabel(line, text="voltam no início do turno do monstro", font=ctk.CTkFont(size=9, slant="italic"),
                     text_color=TEXT_FAINT).pack(side=tk.LEFT)

    def _legendary_step(self, delta):
        leg = self.sheet["lendarias"]
        value = max(0, min(leg["atual"] + delta, leg["max"]))
        if value != leg["atual"]:
            leg["atual"] = value
            self._changed()

    def _legendary_reset(self):
        leg = self.sheet["lendarias"]
        if leg["atual"] != leg["max"]:
            leg["atual"] = leg["max"]
            self._changed()

    ACTION_ADD_COLS = [(150, True), (90, False), (110, False)]

    def _populate_actions(self):
        """Ações em ordem de tipo (ações, ações bônus, reações, lendárias). Mudar o tipo reordena a lista."""
        view = self.actions_view
        for child in view.winfo_children():
            child.destroy()
        path = ("acoes",)

        def add(es):
            nome, ataque, dano = (e.get().strip() for e in es)
            self._append(path, {"tipo": "Ação", "nome": nome, "ataque": ataque, "dano": dano, "descricao": ""},
                         es, self._populate_actions)

        scroll = self._list_section(view, self.ACTION_ADD_COLS, ("Ação ou ataque", "+4 ou DES", "1d6+DES cortante"),
                                    add)
        acoes = self.sheet["acoes"]

        def item(idx):
            return acoes[idx] if idx < len(acoes) else {}

        for idx in sorted(range(len(acoes)), key=lambda i: dnd.TIPOS_ACAO.index(acoes[i]["tipo"])):
            base = path + (idx,)
            row = ctk.CTkFrame(scroll, fg_color=PANEL)
            row.pack(fill=tk.X, pady=3, padx=4)
            line = ctk.CTkFrame(row, fg_color="transparent")
            line.pack(fill=tk.X)
            small_button(line, "X", lambda i=idx: self._remove(path, i, self._populate_actions), width=24,
                         danger=True, height=20).pack(side=tk.RIGHT, padx=8)
            menu = self._option(line, base + ("tipo",), dnd.TIPOS_ACAO, width=100)
            menu.configure(command=lambda label, b=base: (self._commit(b + ("tipo",), label),
                                                          self.after_idle(self._populate_actions)))
            menu.pack(side=tk.LEFT, padx=(6, 3), pady=3)
            self._field(line, base + ("nome",), width=80, transparent=True, bold=True, size=12).pack(
                side=tk.LEFT, padx=3, fill=tk.X, expand=True)

            rolls_line = ctk.CTkFrame(row, fg_color="transparent")
            rolls_line.pack(fill=tk.X, padx=(6, 0))
            self._roll_button(rolls_line, lambda i=idx: dnd.ataque_request(
                self.sheet, item(i).get("ataque"), item(i).get("nome") or "Ataque"), text="Ataque", width=70).pack(
                side=tk.LEFT, padx=(4, 0))
            self._field(rolls_line, base + ("ataque",), width=80, height=22, placeholder="—").pack(
                side=tk.LEFT, padx=(4, 12))
            self._roll_button(rolls_line, lambda i=idx: dnd.dano_request(
                self.sheet, item(i).get("dano"), f"{item(i).get('nome') or 'Ataque'} (dano)"), text="Dano",
                width=64).pack(side=tk.LEFT)
            self._field(rolls_line, base + ("dano",), width=150, height=22, placeholder="—").pack(
                side=tk.LEFT, padx=(4, 12), fill=tk.X, expand=True)
            self._textbox(row, base + ("descricao",), auto_height=True, text_color=TEXT_DIM,
                          placeholder="Alcance, alvos, efeito, CD de resistência, recarga...").pack(
                fill=tk.X, padx=6, pady=(0, 6))
        ctk.CTkLabel(view, text="Ataque: número (+4) ou atributo (DES = atributo + proficiência do ND). "
                                "Dano: 1d6+DES usa o modificador. Shift = vantagem, Ctrl = desvantagem.",
                     font=ctk.CTkFont(size=9, slant="italic"), text_color=TEXT_FAINT).pack(anchor=tk.W, pady=(4, 0))

    HABILIDADE_COLS = [(200, True), (200, True)]

    def _populate_abilities(self):
        view = self.abilities_view
        for child in view.winfo_children():
            child.destroy()
        keys, path = ("nome", "descricao"), ("habilidades",)
        scroll = self._list_section(
            view, self.HABILIDADE_COLS, ("Habilidade (ex.: Fuga Ágil)", "Descrição"),
            lambda es: self._append(path, {k: e.get().strip() for k, e in zip(keys, es)}, es,
                                    self._populate_abilities))
        self._list_rows(scroll, path, self.sheet["habilidades"], self.HABILIDADE_COLS, keys,
                        lambda i: self._remove(path, i, self._populate_abilities), wrap_key="descricao",
                        placeholder="O que a habilidade faz...")
