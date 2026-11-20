"""Tela da ficha de Ordem Paranormal (mesma interface do mestre, do jogador e do modo offline).

Todos os campos são editáveis no lugar. Cada campo é registrado com o caminho dele na ficha
(ex.: ("pv", "atual")); quando chega uma ficha nova pela rede, só os campos que mudaram são
reescritos, e o campo em que a pessoa está digitando não é tocado.
"""
import tkinter as tk

import customtkinter as ctk

from src import ordem
from src.sheet_io import to_int
from src.ui.common import (BORDER, BUTTON, BUTTON_HOVER, INPUT, PANEL, PANEL_DARK, TEXT, TEXT_DIM, TEXT_FAINT,
                           TEXT_MUTED, TITLE_FONT, TabBar, fmt_bonus, small_button)

SYSTEM = ordem.SYSTEM
RESOURCE_COLORS = {"pv": "#c0392b", "pe": "#d4a017", "san": "#2e86c1"}
TABS = ["Perícias", "Ataques", "Habilidades", "Inventário", "Descrição"]


class SheetView(ctk.CTkFrame):
    def __init__(self, master, sheet: dict, on_change=None):
        super().__init__(master, fg_color="transparent")
        self.sheet = sheet
        self.on_change = on_change
        self.color = sheet.get("cor", "#8e44ad")
        self._build()

    # ================================================================= API
    def set_sheet(self, new_sheet: dict):
        if not new_sheet or new_sheet == self.sheet:
            return
        old, self.sheet = self.sheet, new_sheet
        if old.get("cor") != new_sheet.get("cor"):
            self._rebuild()
            return
        if len(old.get("ataques", [])) != len(new_sheet.get("ataques", [])):
            self._populate_attacks()
        if len(old.get("habilidades", [])) != len(new_sheet.get("habilidades", [])):
            self._populate_abilities()
        if len(old.get("inventario", {}).get("itens", [])) != len(new_sheet.get("inventario", {}).get("itens", [])):
            self._populate_items()
        self._sync_fields()
        self._refresh_computed()

    # ================================================================= caminho na ficha
    def _get(self, path):
        value = self.sheet
        for key in path:
            try:
                value = value[key]
            except (KeyError, IndexError, TypeError):
                return None
        return value

    def _set(self, path, value):
        target = self.sheet
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value

    # ================================================================= campos registrados
    def _field(self, parent, path, kind="str", width=60, placeholder="", size=11, bold=False, justify="left",
               clamp=None, transparent=False, text_color=TEXT, height=26):
        entry = ctk.CTkEntry(
            parent, width=width, height=height, placeholder_text=placeholder, justify=justify,
            font=ctk.CTkFont(size=size, weight="bold" if bold else "normal"), text_color=text_color,
            fg_color="transparent" if transparent else INPUT, border_width=0 if transparent else 1,
            border_color=BORDER,
        )
        self._write(entry, self._get(path), kind)
        self.fields.append((entry, path, kind))

        def save(defocus):
            try:
                raw = entry.get()
            except tk.TclError:
                return
            current = self._get(path)
            if kind == "int":
                value = to_int(raw, current if isinstance(current, int) else 0)
                if clamp:
                    value = clamp(value)
            else:
                value = raw.strip()
            if value != current:
                self._set(path, value)
                self._changed()
            self._sync_fields()
            if defocus:
                self.winfo_toplevel().focus()

        entry.bind("<Return>", lambda e: save(True))
        entry.bind("<FocusOut>", lambda e: save(False))
        return entry

    def _textbox(self, parent, path):
        box = ctk.CTkTextbox(parent, height=110, fg_color=INPUT, border_color=BORDER, border_width=1,
                             font=ctk.CTkFont(size=11), wrap="word")
        self._write(box, self._get(path), "text")
        self.fields.append((box, path, "text"))

        def save(_event=None):
            try:
                value = box.get("1.0", "end-1c").strip()
            except tk.TclError:
                return
            if value != self._get(path):
                self._set(path, value)
                self._changed()

        box.bind("<FocusOut>", save)
        return box

    @staticmethod
    def _write(widget, value, kind):
        text = "" if value is None else str(value)
        if kind == "text":
            widget.delete("1.0", "end")
            widget.insert("1.0", text)
        else:
            widget.delete(0, tk.END)
            if text:
                widget.insert(0, text)

    def _has_focus(self, widget):
        focus = self.focus_get()
        inner = getattr(widget, "_entry", None) or getattr(widget, "_textbox", None)
        return focus is not None and focus in (widget, inner)

    def _sync_fields(self):
        """Reescreve os campos que não batem com a ficha (menos o que está sendo editado)."""
        alive = []
        for widget, path, kind in self.fields:
            if not widget.winfo_exists():
                continue
            alive.append((widget, path, kind))
            if self._has_focus(widget):
                continue
            value = self._get(path)
            text = "" if value is None else str(value)
            current = widget.get("1.0", "end-1c") if kind == "text" else widget.get()
            if current != text:
                self._write(widget, value, kind)
        self.fields = alive

    def _computed(self, fn):
        """Registra algo calculado (rótulo, barra) para atualizar depois de cada mudança."""
        self.computed.append(fn)
        fn()

    def _refresh_computed(self):
        alive = []
        for fn in self.computed:
            try:
                fn()
                alive.append(fn)
            except tk.TclError:
                pass  # widget destruído
        self.computed = alive

    def _changed(self):
        self._refresh_computed()
        if self.on_change:
            self.on_change(self.sheet)

    # ================================================================= construção
    def _get_color(self):
        return self.color

    def _card(self, parent, title=None, **pack):
        card = ctk.CTkFrame(parent, fg_color=PANEL, border_color=self.color, border_width=2, corner_radius=10)
        card.pack(**pack)
        if title:
            ctk.CTkLabel(card, text=title, font=ctk.CTkFont(family=TITLE_FONT, size=13, weight="bold"),
                         text_color=TEXT).pack(pady=(8, 4))
        return card

    @staticmethod
    def _caption(parent, text):
        return ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(size=9, weight="bold"), text_color=TEXT_MUTED)

    def _rebuild(self):
        active = self.tabs.active if hasattr(self, "tabs") else None
        for child in self.winfo_children():
            child.destroy()
        self.color = self.sheet.get("cor", self.color)
        self._build(active)

    def _build(self, active_tab=None):
        self.fields = []
        self.computed = []

        header = self._card(self, fill=tk.X, padx=10, pady=(5, 10))
        self._field(header, ("nome",), width=380, size=20, bold=True, transparent=True, text_color=self.color,
                    placeholder="Nome do personagem", height=36).pack(side=tk.LEFT, padx=14, pady=8)
        right = ctk.CTkFrame(header, fg_color="transparent")
        right.pack(side=tk.RIGHT, padx=14)
        self._caption(right, "JOGADOR").pack(side=tk.LEFT, padx=(0, 6))
        self._field(right, ("jogador",), width=160).pack(side=tk.LEFT)
        self.lbl_title = ctk.CTkLabel(right, text="", font=ctk.CTkFont(size=12), text_color=TEXT_DIM)
        self.lbl_title.pack(side=tk.LEFT, padx=(16, 0))
        self._computed(lambda: self.lbl_title.configure(
            text=f"{self.sheet.get('classe') or 'Sem classe'}  |  NEX {self.sheet.get('nex', 0)}%"))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        left = self.left_column = ctk.CTkScrollableFrame(body, fg_color="transparent", width=380)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        right_col = ctk.CTkFrame(body, fg_color="transparent")
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self._build_attributes(left)
        self._build_status(left)
        self._build_identity(left)
        self._build_defense(left)
        self._build_tabs(right_col, active_tab)

    # ----------------------------------------------------------------- coluna esquerda
    def _build_attributes(self, parent):
        card = self._card(parent, "ATRIBUTOS", fill=tk.X, pady=(0, 10))
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill=tk.X, padx=10, pady=(0, 12))
        for idx, (key, sigla, nome) in enumerate(ordem.ATRIBUTOS):
            row.grid_columnconfigure(idx, weight=1)
            box = ctk.CTkFrame(row, fg_color=PANEL_DARK, corner_radius=6)
            box.grid(row=0, column=idx, padx=3, sticky="nsew")
            self._caption(box, sigla).pack(pady=(6, 0))
            self._field(box, ("atributos", key), kind="int", width=46, size=22, bold=True, justify="center",
                        transparent=True, clamp=lambda v: max(0, v), height=34).pack(pady=(0, 2))
            ctk.CTkLabel(box, text=nome, font=ctk.CTkFont(size=8), text_color=TEXT_FAINT).pack(pady=(0, 6))

    def _build_status(self, parent):
        card = self._card(parent, None, fill=tk.X, pady=(0, 10))
        for key, sigla, nome in ordem.RECURSOS:
            self._resource(card, key, sigla, nome)

    def _resource(self, parent, key, sigla, nome):
        color = RESOURCE_COLORS[key]
        frame = ctk.CTkFrame(parent, fg_color=PANEL_DARK, corner_radius=8)
        frame.pack(fill=tk.X, padx=12, pady=6)
        top = ctk.CTkFrame(frame, fg_color="transparent")
        top.pack(fill=tk.X, padx=10, pady=(6, 0))
        ctk.CTkLabel(top, text=sigla, font=ctk.CTkFont(size=16, weight="bold"), text_color=color).pack(side=tk.LEFT)
        ctk.CTkLabel(top, text=nome.upper(), font=ctk.CTkFont(size=9, weight="bold"),
                     text_color=TEXT_MUTED).pack(side=tk.LEFT, padx=8)

        vals = ctk.CTkFrame(top, fg_color="transparent")
        vals.pack(side=tk.RIGHT)
        self._field(vals, (key, "atual"), kind="int", width=48, size=16, bold=True, justify="center",
                    clamp=lambda v, k=key: max(0, min(v, self.sheet[k]["max"]))).pack(side=tk.LEFT)
        ctk.CTkLabel(vals, text="/", font=ctk.CTkFont(size=16), text_color=TEXT_MUTED).pack(side=tk.LEFT, padx=4)
        self._field(vals, (key, "max"), kind="int", width=48, size=16, justify="center",
                    clamp=lambda v, k=key: self._set_resource_max(k, v)).pack(side=tk.LEFT)

        bar = ctk.CTkProgressBar(frame, fg_color=BUTTON, progress_color=color, height=8)
        bar.pack(fill=tk.X, padx=10, pady=6)
        self._computed(lambda k=key, b=bar: b.set(self.sheet[k]["atual"] / max(1, self.sheet[k]["max"])))

        ctrl = ctk.CTkFrame(frame, fg_color="transparent")
        ctrl.pack(pady=(0, 8))
        for delta in (-5, -1, 1, 5):
            small_button(ctrl, fmt_bonus(delta) if delta > 0 else str(delta),
                         lambda d=delta, k=key: self._adjust(k, d)).pack(side=tk.LEFT, padx=3)

    def _set_resource_max(self, key, value):
        value = max(0, value)
        if self.sheet[key]["atual"] > value:
            self.sheet[key]["atual"] = value
        return value

    def _adjust(self, key, delta):
        res = self.sheet[key]
        value = max(0, min(res["atual"] + delta, res["max"]))
        if value != res["atual"]:
            res["atual"] = value
            self._sync_fields()
            self._changed()

    def _build_identity(self, parent):
        card = self._card(parent, None, fill=tk.X, pady=(0, 10))
        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(fill=tk.X, padx=12, pady=10)
        grid.grid_columnconfigure(1, weight=1)
        rows = [("ORIGEM", ("origem",), "str"), ("CLASSE", ("classe",), "str")]
        for r, (label, path, kind) in enumerate(rows):
            self._caption(grid, label).grid(row=r, column=0, sticky="w", pady=3, padx=(0, 8))
            self._field(grid, path, kind=kind, width=200).grid(row=r, column=1, sticky="ew", pady=3)

        small = ctk.CTkFrame(card, fg_color="transparent")
        small.pack(fill=tk.X, padx=12, pady=(0, 10))
        for idx, (label, path, kind, suffix) in enumerate([
            ("NEX", ("nex",), "int", "%"), ("PE / RODADA", ("pe_rodada",), "int", ""),
            ("DESLOCAMENTO", ("deslocamento",), "str", ""),
        ]):
            small.grid_columnconfigure(idx, weight=1)
            box = ctk.CTkFrame(small, fg_color=PANEL_DARK, corner_radius=6)
            box.grid(row=0, column=idx, padx=3, sticky="nsew")
            self._caption(box, label).pack(pady=(5, 0))
            line = ctk.CTkFrame(box, fg_color="transparent")
            line.pack(pady=(0, 6))
            clamp = (lambda v: max(0, min(v, 100))) if path == ("nex",) else ((lambda v: max(0, v)) if kind == "int" else None)
            self._field(line, path, kind=kind, width=50, size=15, bold=True, justify="center", transparent=True,
                        clamp=clamp).pack(side=tk.LEFT)
            if suffix:
                ctk.CTkLabel(line, text=suffix, text_color=TEXT_MUTED).pack(side=tk.LEFT)

    def _build_defense(self, parent):
        card = self._card(parent, None, fill=tk.X, pady=(0, 10))
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill=tk.X, padx=12, pady=(10, 4))
        shield = ctk.CTkFrame(top, fg_color=PANEL_DARK, corner_radius=8, width=74, height=64)
        shield.pack(side=tk.LEFT)
        shield.pack_propagate(False)
        self._caption(shield, "DEFESA").pack(pady=(5, 0))
        total = ctk.CTkLabel(shield, text="", font=ctk.CTkFont(size=22, weight="bold"), text_color=TEXT)
        total.pack()
        self._computed(lambda: total.configure(text=str(ordem.defesa_total(self.sheet))))

        formula = ctk.CTkFrame(top, fg_color="transparent")
        formula.pack(side=tk.LEFT, padx=10)
        agi = ctk.CTkLabel(formula, text="", font=ctk.CTkFont(size=12), text_color=TEXT_DIM)
        agi.pack(side=tk.LEFT)
        self._computed(lambda: agi.configure(text=f"= 10 + AGI ({self.sheet['atributos']['agi']}) +"))
        for idx, (label, key) in enumerate((("Equip.", "equipamento"), ("Outros", "outros"))):
            col = ctk.CTkFrame(formula, fg_color="transparent")
            col.pack(side=tk.LEFT, padx=3)
            self._field(col, ("defesa", key), kind="int", width=40, justify="center").pack()
            ctk.CTkLabel(col, text=label, font=ctk.CTkFont(size=8), text_color=TEXT_FAINT).pack()
            if idx == 0:
                ctk.CTkLabel(formula, text="+", text_color=TEXT_DIM).pack(side=tk.LEFT)

        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(fill=tk.X, padx=12, pady=(4, 10))
        grid.grid_columnconfigure(1, weight=1)
        for r, (label, key) in enumerate((("PROTEÇÃO", "protecao"), ("RESISTÊNCIAS", "resistencias"))):
            self._caption(grid, label).grid(row=r, column=0, sticky="w", pady=3, padx=(0, 8))
            self._field(grid, (key,), width=200).grid(row=r, column=1, sticky="ew", pady=3)

    # ----------------------------------------------------------------- abas
    def _build_tabs(self, parent, active_tab):
        container = self._card(parent, None, fill=tk.BOTH, expand=True)
        content = ctk.CTkFrame(container, fg_color="transparent")
        self.tabs = TabBar(container, content, self._get_color, main=True)
        self.tabs.header.pack(fill=tk.X, side=tk.TOP)
        content.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        views = {name: ctk.CTkFrame(content, fg_color="transparent") for name in TABS}
        for name in TABS:
            self.tabs.add(name, views[name])
        self._build_skills(views["Perícias"])
        self.attacks_view = views["Ataques"]
        self._populate_attacks()
        self._build_abilities(views["Habilidades"])
        self._build_inventory(views["Inventário"])
        self._build_description(views["Descrição"])
        self.tabs.switch(active_tab if active_tab in views else None)

    def _build_skills(self, view):
        head = ctk.CTkFrame(view, fg_color=PANEL_DARK, corner_radius=5)
        head.pack(fill=tk.X, pady=(0, 6))
        scroll = ctk.CTkScrollableFrame(view, fg_color=PANEL_DARK)
        scroll.pack(fill=tk.BOTH, expand=True)
        widths = (24, 230, 50, 60, 56, 56, 60)
        for col, (text, w) in enumerate(zip(("", "PERÍCIA", "ATRIB.", "DADOS", "TREINO", "OUTROS", "BÔNUS"), widths)):
            for frame in (head, scroll):
                frame.grid_columnconfigure(col, minsize=w, weight=1 if col == 1 else 0)
            self._caption(head, text).grid(row=0, column=col, sticky="w" if col == 1 else "", pady=5)

        for r, (key, nome, attr, so_treinada, carga) in enumerate(ordem.PERICIAS):
            marks = ("*" if so_treinada else "") + ("+" if carga else "")
            dot = ctk.CTkLabel(scroll, text="", font=ctk.CTkFont(size=13))
            dot.grid(row=r, column=0, pady=1)
            self._computed(lambda k=key, d=dot: d.configure(
                text="●" if self.sheet["pericias"][k]["treino"] > 0 else "○",
                text_color=self.color if self.sheet["pericias"][k]["treino"] > 0 else "#444444"))

            name_cell = ctk.CTkFrame(scroll, fg_color="transparent")
            name_cell.grid(row=r, column=1, sticky="w")
            ctk.CTkLabel(name_cell, text=f"{nome.upper()}{marks}", font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=TEXT).pack(side=tk.LEFT)
            if key == "profissao":
                self._field(name_cell, ("profissao_nome",), width=110, placeholder="qual?", height=22).pack(side=tk.LEFT, padx=6)

            ctk.CTkLabel(scroll, text=attr.upper(), font=ctk.CTkFont(size=10), text_color=TEXT_MUTED).grid(row=r, column=2)
            dice = ctk.CTkLabel(scroll, text="", font=ctk.CTkFont(size=11), text_color=TEXT_DIM)
            dice.grid(row=r, column=3)
            self._computed(lambda a=attr, d=dice: d.configure(text=f"{self.sheet['atributos'][a]}d20"))
            for col, part in ((4, "treino"), (5, "outros")):
                self._field(scroll, ("pericias", key, part), kind="int", width=40, justify="center",
                            height=22).grid(row=r, column=col, pady=1)
            bonus = ctk.CTkLabel(scroll, text="", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT)
            bonus.grid(row=r, column=6)
            self._computed(lambda k=key, b=bonus: b.configure(text=fmt_bonus(ordem.bonus_pericia(self.sheet, k))))

        ctk.CTkLabel(view, text="+ Penalidade de carga.   * Somente treinada.", font=ctk.CTkFont(size=9, slant="italic"),
                     text_color=TEXT_FAINT).pack(anchor=tk.W, pady=(4, 0))

    # ----------------------------------------------------------------- listas editáveis
    def _list_section(self, view, columns, placeholders, on_add):
        """Linha de 'adicionar' + área rolável. columns = [(largura, expande)]."""
        add = ctk.CTkFrame(view, fg_color="transparent")
        add.pack(fill=tk.X, pady=(0, 8))
        entries = []
        for (width, expand), placeholder in zip(columns, placeholders):
            entry = ctk.CTkEntry(add, width=width, height=26, placeholder_text=placeholder, fg_color=INPUT,
                                 border_color=BORDER, font=ctk.CTkFont(size=11))
            entry.pack(side=tk.LEFT, padx=3, fill=tk.X if expand else None, expand=expand)
            entries.append(entry)
        button = ctk.CTkButton(add, text="Adicionar", width=80, height=26, fg_color=BUTTON, hover_color=BUTTON_HOVER,
                               font=ctk.CTkFont(size=11), command=lambda: on_add(entries))
        button.pack(side=tk.RIGHT, padx=(5, 0))
        for entry in entries:
            entry.bind("<Return>", lambda e: button.invoke())
        scroll = ctk.CTkScrollableFrame(view, fg_color=PANEL_DARK)
        scroll.pack(fill=tk.BOTH, expand=True)
        return scroll

    def _list_rows(self, scroll, base_path, items, columns, keys, on_remove, first_bold=True):
        for child in scroll.winfo_children():
            child.destroy()
        for idx in range(len(items)):
            row = ctk.CTkFrame(scroll, fg_color=PANEL)
            row.pack(fill=tk.X, pady=3, padx=4)
            for c, ((width, expand), key) in enumerate(zip(columns, keys)):
                kind = "int" if key == "espacos" else "str"
                entry = self._field(row, base_path + (idx, key), kind=kind, width=width, transparent=True,
                                    bold=first_bold and c == 0, size=12 if c == 0 else 11,
                                    text_color=self.color if first_bold and c == 0 else TEXT,
                                    justify="center" if kind == "int" else "left")
                entry.pack(side=tk.LEFT, padx=3, pady=3, fill=tk.X if expand else None, expand=expand)
            small_button(row, "X", lambda i=idx: on_remove(i), width=24, danger=True,
                         height=20).pack(side=tk.RIGHT, padx=8)

    def _append(self, path, item, entries, repopulate):
        if not item.get("nome"):
            return
        target = self._get(path)
        target.append(item)
        for entry in entries:
            entry.delete(0, tk.END)
        repopulate()
        self._changed()

    def _remove(self, path, idx, repopulate):
        items = self._get(path)
        if idx < len(items):
            items.pop(idx)
            repopulate()
            self._changed()

    # Ataques
    ATTACK_COLS = [(140, True), (90, False), (80, False), (140, True)]

    def _populate_attacks(self):
        view = self.attacks_view
        for child in view.winfo_children():
            child.destroy()
        keys = ("nome", "teste", "dano", "especial")
        self.attacks_scroll = self._list_section(
            view, self.ATTACK_COLS, ("Ataque", "Teste", "Dano", "Crítico / Alcance / Especial"),
            lambda es: self._append(("ataques",), {k: e.get().strip() for k, e in zip(keys, es)}, es,
                                    self._populate_attacks))
        self._list_rows(self.attacks_scroll, ("ataques",), self.sheet["ataques"], self.ATTACK_COLS, keys,
                        lambda i: self._remove(("ataques",), i, self._populate_attacks))

    # Habilidades & Rituais
    ABILITY_COLS = [(150, True), (55, False), (45, False), (170, True)]

    def _build_abilities(self, view):
        top = ctk.CTkFrame(view, fg_color="transparent")
        top.pack(fill=tk.X, pady=(0, 8))
        self._caption(top, "DT DE RITUAIS").pack(side=tk.LEFT, padx=(4, 8))
        self._field(top, ("dt_rituais",), kind="int", width=50, justify="center", size=14, bold=True).pack(side=tk.LEFT)
        self.abilities_view = ctk.CTkFrame(view, fg_color="transparent")
        self.abilities_view.pack(fill=tk.BOTH, expand=True)
        self._populate_abilities()

    def _populate_abilities(self):
        view = self.abilities_view
        for child in view.winfo_children():
            child.destroy()
        keys = ("nome", "custo", "pagina", "descricao")
        scroll = self._list_section(
            view, self.ABILITY_COLS, ("Habilidade ou ritual", "Custo", "Pág.", "Descrição"),
            lambda es: self._append(("habilidades",), {k: e.get().strip() for k, e in zip(keys, es)}, es,
                                    self._populate_abilities))
        self._list_rows(scroll, ("habilidades",), self.sheet["habilidades"], self.ABILITY_COLS, keys,
                        lambda i: self._remove(("habilidades",), i, self._populate_abilities))

    # Inventário
    ITEM_COLS = [(300, True), (80, False), (70, False)]

    def _build_inventory(self, view):
        top = ctk.CTkFrame(view, fg_color=PANEL_DARK, corner_radius=6)
        top.pack(fill=tk.X, pady=(0, 8))
        line1 = ctk.CTkFrame(top, fg_color="transparent")
        line1.pack(fill=tk.X, padx=8, pady=(8, 4))
        self._caption(line1, "PONTOS DE PRESTÍGIO").pack(side=tk.LEFT)
        self._field(line1, ("inventario", "pontos_prestigio"), kind="int", width=50, justify="center").pack(side=tk.LEFT, padx=(6, 16))
        self._caption(line1, "PATENTE").pack(side=tk.LEFT)
        self._field(line1, ("inventario", "patente"), width=160).pack(side=tk.LEFT, padx=6, fill=tk.X, expand=True)

        line2 = ctk.CTkFrame(top, fg_color="transparent")
        line2.pack(fill=tk.X, padx=8, pady=(0, 8))
        self._caption(line2, "LIMITE DE ITENS").pack(side=tk.LEFT, padx=(0, 4))
        for cat in ordem.CATEGORIAS:
            ctk.CTkLabel(line2, text=cat, font=ctk.CTkFont(size=10), text_color=TEXT_MUTED).pack(side=tk.LEFT, padx=(6, 2))
            self._field(line2, ("inventario", "limite_itens", cat), kind="int", width=34, justify="center",
                        clamp=lambda v: max(0, v)).pack(side=tk.LEFT)
        self._caption(line2, "CRÉDITO").pack(side=tk.LEFT, padx=(14, 4))
        self._field(line2, ("inventario", "limite_credito"), width=90).pack(side=tk.LEFT)
        self._caption(line2, "CARGA").pack(side=tk.LEFT, padx=(14, 4))
        used = ctk.CTkLabel(line2, text="", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT)
        used.pack(side=tk.LEFT)
        self._computed(lambda: used.configure(
            text=f"{ordem.espacos_usados(self.sheet)} /",
            text_color="#e74c3c" if ordem.espacos_usados(self.sheet) > self.sheet["inventario"]["carga_max"] else TEXT))
        self._field(line2, ("inventario", "carga_max"), kind="int", width=40, justify="center",
                    clamp=lambda v: max(0, v)).pack(side=tk.LEFT, padx=4)

        self.items_view = ctk.CTkFrame(view, fg_color="transparent")
        self.items_view.pack(fill=tk.BOTH, expand=True)
        self._populate_items()

    def _populate_items(self):
        view = self.items_view
        for child in view.winfo_children():
            child.destroy()
        keys = ("nome", "categoria", "espacos")
        path = ("inventario", "itens")

        def add(es):
            item = {"nome": es[0].get().strip(), "categoria": es[1].get().strip(), "espacos": max(0, to_int(es[2].get(), 1))}
            self._append(path, item, es, self._populate_items)

        scroll = self._list_section(view, self.ITEM_COLS, ("Item", "Categoria", "Espaços"), add)
        self._list_rows(scroll, path, self.sheet["inventario"]["itens"], self.ITEM_COLS, keys,
                        lambda i: self._remove(path, i, self._populate_items), first_bold=False)

    # Descrição
    def _build_description(self, view):
        for idx, (key, label) in enumerate(ordem.DESCRICAO):
            r, c = divmod(idx, 2)
            view.grid_columnconfigure(c, weight=1)
            view.grid_rowconfigure(r, weight=1)
            cell = ctk.CTkFrame(view, fg_color=PANEL_DARK, corner_radius=6)
            cell.grid(row=r, column=c, padx=4, pady=4, sticky="nsew")
            self._caption(cell, label.upper()).pack(anchor=tk.W, padx=8, pady=(6, 2))
            self._textbox(cell, ("descricao", key)).pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))
