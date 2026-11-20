"""Tela da ficha de Ordem Paranormal (mesma interface do mestre, do jogador e do modo offline).

Os campos são editáveis no lugar e registrados com o caminho deles na ficha (ex.: ("pv", "atual")).
Depois de cada edição as regras do livro são reaplicadas (src/ordem.apply_rules) e os valores
calculados são redesenhados. Quando chega uma ficha nova pela rede, só os campos que mudaram são
reescritos, e o campo em que a pessoa está digitando não é tocado.
"""
import tkinter as tk
import tkinter.font  # noqa: F401  (tk.font, usado para medir a altura das linhas)

import customtkinter as ctk

from src import ordem
from src.sheet_io import to_int
from src.ui.common import (BORDER, BUTTON, BUTTON_HOVER, ERROR, INPUT, PANEL, PANEL_DARK, TEXT, TEXT_DIM,
                           TEXT_FAINT, TEXT_MUTED, TITLE_FONT, TabBar, fmt_bonus, small_button)

SYSTEM = ordem.SYSTEM
RESOURCE_COLORS = {"pv": "#c0392b", "pe": "#d4a017", "san": "#2e86c1"}
TABS = ["Perícias", "Ataques", "Habilidades", "Inventário", "Descrição"]
CLASS_NAMES = [c["nome"] for c in ordem.CLASSES.values()]
GRADE_LABELS = {value: label for value, label in ordem.GRAUS}
GRADE_VALUES = {label: value for value, label in ordem.GRAUS}


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
        if old.get("cor") != new_sheet.get("cor") or ordem.class_key(old) != ordem.class_key(new_sheet):
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
    @staticmethod
    def _display(value, kind):
        if kind == "grade":
            return GRADE_LABELS.get(value, GRADE_LABELS[0])
        return "" if value is None else str(value)

    @staticmethod
    def _read(widget, kind):
        if kind == "text":
            return widget.get("1.0", "end-1c")
        return widget.get()

    def _write(self, widget, value, kind):
        text = self._display(value, kind)
        if kind == "text":
            widget.delete("1.0", "end")
            widget.insert("1.0", text)
        elif kind in ("combo", "grade"):
            widget.set(text)
        else:
            widget.delete(0, tk.END)
            if text:
                widget.insert(0, text)

    def _commit(self, path, value):
        """Grava um valor editado, reaplica as regras e avisa quem estiver ouvindo."""
        if value == self._get(path):
            self._sync_fields()
            return
        self._set(path, value)
        self._changed()

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
            self._commit(path, value)
            if defocus:
                self.winfo_toplevel().focus()

        entry.bind("<Return>", lambda e: save(True))
        entry.bind("<FocusOut>", lambda e: save(False))
        return entry

    def _combo(self, parent, path, values, width=200):
        """Caixa com lista (dá para escolher ou digitar)."""
        combo = ctk.CTkComboBox(parent, values=values, width=width, height=26, fg_color=INPUT, border_color=BORDER,
                                button_color=BUTTON, button_hover_color=BUTTON_HOVER, font=ctk.CTkFont(size=11),
                                command=lambda v: self._commit(path, v.strip()))
        self._write(combo, self._get(path), "combo")
        self.fields.append((combo, path, "combo"))

        def save(_event=None):
            try:
                self._commit(path, combo.get().strip())
            except tk.TclError:
                pass

        combo.bind("<Return>", save)
        combo.bind("<FocusOut>", save)
        return combo

    def _grade(self, parent, path):
        """Menu do grau de treinamento (Destreinado/Treinado/Veterano/Expert)."""
        menu = ctk.CTkOptionMenu(parent, values=list(GRADE_VALUES), width=104, height=22, fg_color=INPUT,
                                 button_color=BUTTON, button_hover_color=BUTTON_HOVER, font=ctk.CTkFont(size=10),
                                 dropdown_font=ctk.CTkFont(size=11),
                                 command=lambda label: self._commit(path, GRADE_VALUES[label]))
        self._write(menu, self._get(path), "grade")
        self.fields.append((menu, path, "grade"))
        return menu

    def _textbox(self, parent, path, auto_height=False, text_color=TEXT):
        """Texto com quebra de linha. Com auto_height, a altura acompanha o tamanho do texto."""
        box = ctk.CTkTextbox(parent, height=28 if auto_height else 110, wrap="word", font=ctk.CTkFont(size=11),
                             text_color=text_color,
                             fg_color="transparent" if auto_height else INPUT,
                             border_color=BORDER, border_width=0 if auto_height else 1,
                             activate_scrollbars=not auto_height)
        self._write(box, self._get(path), "text")
        self.fields.append((box, path, "text"))

        if auto_height:
            def fit(_event=None):
                try:
                    inner = box._textbox
                    content = inner.count("1.0", "end", "ypixels")  # altura real do texto, já com as quebras
                    content = content[0] if isinstance(content, tuple) else (content or 0)
                    content = max(content, tk.font.Font(font=inner.cget("font")).metrics("linespace"))
                    # + margens internas do CTkTextbox (pady do texto e 6 px do grid) e uma folga
                    height = (content + 2 * int(inner.cget("pady"))) / box._get_widget_scaling() + 14
                    if abs(box.cget("height") - height) > 1:
                        box.configure(height=height)
                except (tk.TclError, AttributeError):
                    pass

            box._fit = fit
            box.bind("<KeyRelease>", fit)
            box.bind("<FocusOut>", lambda e: box.after_idle(fit), add="+")
            box._textbox.bind("<Configure>", fit, add="+")
            box.after_idle(fit)

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
            if self._read(widget, kind) != self._display(value, kind):
                self._write(widget, value, kind)
                if hasattr(widget, "_fit"):
                    widget.after_idle(widget._fit)
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
        old_class = self._built_class
        ordem.apply_rules(self.sheet)
        if ordem.class_key(self.sheet) != old_class:
            self.after_idle(self._rebuild)  # troca campos manuais por calculados (ou o contrário)
        else:
            self._sync_fields()
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

    def _value_label(self, parent, fn, size=15, **kwargs):
        """Rótulo com valor calculado, atualizado a cada mudança."""
        label = ctk.CTkLabel(parent, text="", font=ctk.CTkFont(size=size, weight="bold"), text_color=TEXT, **kwargs)
        self._computed(lambda: label.configure(text=str(fn())))
        return label

    def _rebuild(self):
        active = self.tabs.active if hasattr(self, "tabs") else None
        for child in self.winfo_children():
            child.destroy()
        self.color = self.sheet.get("cor", self.color)
        self._build(active)

    def _build(self, active_tab=None):
        self.fields = []
        self.computed = []
        self._built_class = ordem.class_key(self.sheet)

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
        self._build_identity(left)
        self._build_status(left)
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
                        transparent=True, clamp=lambda v: max(0, min(v, 5)), height=34).pack(pady=(0, 2))
            ctk.CTkLabel(box, text=nome, font=ctk.CTkFont(size=8), text_color=TEXT_FAINT).pack(pady=(0, 6))

    def _build_identity(self, parent):
        card = self._card(parent, None, fill=tk.X, pady=(0, 10))
        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(fill=tk.X, padx=12, pady=10)
        grid.grid_columnconfigure(1, weight=1)
        self._caption(grid, "ORIGEM").grid(row=0, column=0, sticky="w", pady=3, padx=(0, 8))
        self._combo(grid, ("origem",), ordem.ORIGEM_NOMES).grid(row=0, column=1, sticky="ew", pady=3)
        origin_info = ctk.CTkLabel(grid, text="", font=ctk.CTkFont(size=10), text_color=TEXT_DIM,
                                   wraplength=280, justify=tk.LEFT, anchor="w")
        origin_info.grid(row=1, column=1, sticky="ew", pady=(0, 4))
        self._computed(lambda: origin_info.configure(text=self._origin_text()))
        self._caption(grid, "CLASSE").grid(row=2, column=0, sticky="w", pady=3, padx=(0, 8))
        self._combo(grid, ("classe",), CLASS_NAMES).grid(row=2, column=1, sticky="ew", pady=3)

        small = ctk.CTkFrame(card, fg_color="transparent")
        small.pack(fill=tk.X, padx=12, pady=(0, 10))
        for idx in range(3):
            small.grid_columnconfigure(idx, weight=1)

        def box(idx, label):
            frame = ctk.CTkFrame(small, fg_color=PANEL_DARK, corner_radius=6)
            frame.grid(row=0, column=idx, padx=3, sticky="nsew")
            self._caption(frame, label).pack(pady=(5, 0))
            line = ctk.CTkFrame(frame, fg_color="transparent")
            line.pack(pady=(0, 6))
            return line

        nex = box(0, "NEX")
        self._field(nex, ("nex",), kind="int", width=40, size=15, bold=True, justify="center", transparent=True,
                    clamp=ordem.nex_valido).pack(side=tk.LEFT)
        ctk.CTkLabel(nex, text="%", text_color=TEXT_MUTED).pack(side=tk.LEFT)
        self._value_label(box(1, "PE / RODADA"), lambda: ordem.pe_por_rodada(self.sheet)).pack(pady=2)
        self._field(box(2, "DESLOCAMENTO"), ("deslocamento",), width=60, size=15, bold=True, justify="center",
                    transparent=True).pack()

    def _origin_text(self):
        info = ordem.origem_info(self.sheet)
        if info is None:
            return "Escolha uma origem da lista para aplicar as perícias e o poder." if self.sheet.get("origem") else ""
        nome, pericias, poder, resumo = info
        nomes = {key: n for key, n, *_ in ordem.PERICIAS}
        treinadas = " e ".join(nomes[k] for k in pericias) or "à escolha do mestre"
        return f"Treinadas: {treinadas}.\n{poder}: {resumo}"

    def _build_status(self, parent):
        card = self._card(parent, None, fill=tk.X, pady=(0, 10))
        if self._built_class is None:
            ctk.CTkLabel(card, text="Escolha Combatente, Especialista ou Ocultista para calcular PV, PE e SAN.",
                         font=ctk.CTkFont(size=10, slant="italic"), text_color=TEXT_FAINT,
                         wraplength=330).pack(padx=12, pady=(8, 0))
        for key, sigla, nome in ordem.RECURSOS:
            self._resource(card, key, sigla, nome)

    def _resource(self, parent, key, sigla, nome):
        color = RESOURCE_COLORS[key]
        auto = self._built_class is not None
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
        if auto:
            self._value_label(vals, lambda k=key: self.sheet[k]["max"], size=16, width=40).pack(side=tk.LEFT)
        else:
            self._field(vals, (key, "max"), kind="int", width=48, size=16, justify="center",
                        clamp=lambda v: max(0, v)).pack(side=tk.LEFT)

        bar = ctk.CTkProgressBar(frame, fg_color=BUTTON, progress_color=color, height=8)
        bar.pack(fill=tk.X, padx=10, pady=6)
        self._computed(lambda k=key, b=bar: b.set(self.sheet[k]["atual"] / max(1, self.sheet[k]["max"])))

        ctrl = ctk.CTkFrame(frame, fg_color="transparent")
        ctrl.pack(fill=tk.X, padx=10, pady=(0, 8))
        buttons = ctk.CTkFrame(ctrl, fg_color="transparent")
        buttons.pack(side=tk.LEFT)
        for delta in (-5, -1, 1, 5):
            small_button(buttons, fmt_bonus(delta) if delta > 0 else str(delta),
                         lambda d=delta, k=key: self._adjust(k, d)).pack(side=tk.LEFT, padx=3)
        if auto:
            bonus = ctk.CTkFrame(ctrl, fg_color="transparent")
            bonus.pack(side=tk.RIGHT)
            ctk.CTkLabel(bonus, text="bônus", font=ctk.CTkFont(size=9), text_color=TEXT_FAINT).pack(side=tk.LEFT, padx=4)
            self._field(bonus, (key, "bonus"), kind="int", width=40, height=22, justify="center").pack(side=tk.LEFT)

    def _adjust(self, key, delta):
        res = self.sheet[key]
        value = max(0, min(res["atual"] + delta, res["max"]))
        if value != res["atual"]:
            res["atual"] = value
            self._changed()

    def _build_defense(self, parent):
        card = self._card(parent, None, fill=tk.X, pady=(0, 10))
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill=tk.X, padx=12, pady=(10, 4))
        shield = ctk.CTkFrame(top, fg_color=PANEL_DARK, corner_radius=8, width=74, height=64)
        shield.pack(side=tk.LEFT)
        shield.pack_propagate(False)
        self._caption(shield, "DEFESA").pack(pady=(5, 0))
        self._value_label(shield, lambda: ordem.defesa_total(self.sheet), size=22).pack()

        formula = ctk.CTkFrame(top, fg_color="transparent")
        formula.pack(side=tk.LEFT, padx=10)
        agi = ctk.CTkLabel(formula, text="", font=ctk.CTkFont(size=12), text_color=TEXT_DIM)
        agi.pack(side=tk.LEFT)
        self._computed(lambda: agi.configure(
            text=f"= 10 + AGI ({self.sheet['atributos']['agi']})"
                 + (f" + {ordem.defesa_origem(self.sheet)} origem" if ordem.defesa_origem(self.sheet) else "") + " +"))
        for idx, (label, key) in enumerate((("Equip.", "equipamento"), ("Outros", "outros"))):
            col = ctk.CTkFrame(formula, fg_color="transparent")
            col.pack(side=tk.LEFT, padx=3)
            self._field(col, ("defesa", key), kind="int", width=40, justify="center").pack()
            ctk.CTkLabel(col, text=label, font=ctk.CTkFont(size=8), text_color=TEXT_FAINT).pack()
            if idx == 0:
                ctk.CTkLabel(formula, text="+", text_color=TEXT_DIM).pack(side=tk.LEFT)

        warn = ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=10, weight="bold"), text_color=ERROR)
        warn.pack(anchor=tk.W, padx=12)
        self._computed(lambda: warn.configure(
            text="Sobrecarregado: −5 na Defesa e nas perícias de carga, −3m de deslocamento"
            if ordem.sobrecarregado(self.sheet) else ""))

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
        widths = (24, 200, 46, 56, 112, 56, 56)
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
                self._field(name_cell, ("profissao_nome",), width=90, placeholder="qual?", height=22).pack(side=tk.LEFT, padx=6)

            ctk.CTkLabel(scroll, text=attr.upper(), font=ctk.CTkFont(size=10), text_color=TEXT_MUTED).grid(row=r, column=2)
            dice = ctk.CTkLabel(scroll, text="", font=ctk.CTkFont(size=11), text_color=TEXT_DIM)
            dice.grid(row=r, column=3)
            self._computed(lambda a=attr, d=dice: d.configure(text=ordem.dados(self.sheet, a)))
            self._grade(scroll, ("pericias", key, "treino")).grid(row=r, column=4, pady=1)
            self._field(scroll, ("pericias", key, "outros"), kind="int", width=40, justify="center",
                        height=22).grid(row=r, column=5, pady=1)
            bonus = ctk.CTkLabel(scroll, text="", font=ctk.CTkFont(size=12, weight="bold"))
            bonus.grid(row=r, column=6)
            self._computed(lambda k=key, b=bonus: b.configure(
                text=fmt_bonus(ordem.bonus_pericia(self.sheet, k)),
                text_color=ERROR if k in ordem.PERICIAS_CARGA and ordem.sobrecarregado(self.sheet) else TEXT))

        ctk.CTkLabel(view, text="+ Penalidade de carga.   * Somente treinada.   2d20↓ = atributo 0: rola 2d20 e fica com o pior.",
                     font=ctk.CTkFont(size=9, slant="italic"), text_color=TEXT_FAINT).pack(anchor=tk.W, pady=(4, 0))

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

    def _list_rows(self, scroll, base_path, items, columns, keys, on_remove, first_bold=True, wrap_key=None):
        """Uma linha editável por item. `wrap_key` vai numa área de texto com quebra de linha embaixo."""
        for child in scroll.winfo_children():
            child.destroy()
        for idx in range(len(items)):
            row = ctk.CTkFrame(scroll, fg_color=PANEL)
            row.pack(fill=tk.X, pady=3, padx=4)
            line = ctk.CTkFrame(row, fg_color="transparent")
            line.pack(fill=tk.X)
            for c, ((width, expand), key) in enumerate(zip(columns, keys)):
                if key == wrap_key:
                    continue
                kind = "int" if key == "espacos" else "str"
                entry = self._field(line, base_path + (idx, key), kind=kind, width=width, transparent=True,
                                    bold=first_bold and c == 0, size=12 if c == 0 else 11,
                                    text_color=self.color if first_bold and c == 0 else TEXT,
                                    justify="center" if kind == "int" else "left")
                entry.pack(side=tk.LEFT, padx=3, pady=3, fill=tk.X if expand else None, expand=expand)
            small_button(line, "X", lambda i=idx: on_remove(i), width=24, danger=True,
                         height=20).pack(side=tk.RIGHT, padx=8)
            if wrap_key:
                self._textbox(row, base_path + (idx, wrap_key), auto_height=True,
                              text_color=TEXT_DIM).pack(fill=tk.X, padx=6, pady=(0, 6))

    def _append(self, path, item, entries, repopulate):
        if not item.get("nome"):
            return
        self._get(path).append(item)
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
        scroll = self._list_section(
            view, self.ATTACK_COLS, ("Ataque", "Teste", "Dano", "Crítico / Alcance / Especial"),
            lambda es: self._append(("ataques",), {k: e.get().strip() for k, e in zip(keys, es)}, es,
                                    self._populate_attacks))
        self._list_rows(scroll, ("ataques",), self.sheet["ataques"], self.ATTACK_COLS, keys,
                        lambda i: self._remove(("ataques",), i, self._populate_attacks))

    # Habilidades & Rituais
    ABILITY_COLS = [(150, True), (55, False), (45, False), (170, True)]

    def _build_abilities(self, view):
        top = ctk.CTkFrame(view, fg_color="transparent")
        top.pack(fill=tk.X, pady=(0, 8))
        self._caption(top, "DT DE RITUAIS").pack(side=tk.LEFT, padx=(4, 8))
        self._value_label(top, lambda: ordem.dt_rituais(self.sheet), size=16).pack(side=tk.LEFT)
        dt_hint = ctk.CTkLabel(top, text="", font=ctk.CTkFont(size=10), text_color=TEXT_FAINT)
        dt_hint.pack(side=tk.LEFT, padx=10)
        self._computed(lambda: dt_hint.configure(
            text=f"= 10 + limite de PE ({ordem.limite_pe(self.sheet)}) + PRE ({self.sheet['atributos']['pre']})"))
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
                        lambda i: self._remove(("habilidades",), i, self._populate_abilities),
                        wrap_key="descricao")

    # Inventário
    ITEM_COLS = [(300, True), (80, False), (70, False)]

    def _build_inventory(self, view):
        top = ctk.CTkFrame(view, fg_color=PANEL_DARK, corner_radius=6)
        top.pack(fill=tk.X, pady=(0, 8))
        line1 = ctk.CTkFrame(top, fg_color="transparent")
        line1.pack(fill=tk.X, padx=8, pady=(8, 4))
        self._caption(line1, "PONTOS DE PRESTÍGIO").pack(side=tk.LEFT)
        self._field(line1, ("inventario", "pontos_prestigio"), kind="int", width=50, justify="center",
                    clamp=lambda v: max(0, v)).pack(side=tk.LEFT, padx=(6, 16))
        self._caption(line1, "PATENTE").pack(side=tk.LEFT)
        self._value_label(line1, lambda: self.sheet["inventario"]["patente"], size=12).pack(side=tk.LEFT, padx=6)
        self._caption(line1, "CRÉDITO").pack(side=tk.LEFT, padx=(16, 0))
        self._value_label(line1, lambda: self.sheet["inventario"]["limite_credito"], size=12).pack(side=tk.LEFT, padx=6)

        line2 = ctk.CTkFrame(top, fg_color="transparent")
        line2.pack(fill=tk.X, padx=8, pady=(0, 8))
        self._caption(line2, "ITENS POR CATEGORIA").pack(side=tk.LEFT, padx=(0, 4))
        for cat in ordem.CATEGORIAS:
            label = ctk.CTkLabel(line2, text="", font=ctk.CTkFont(size=12, weight="bold"))
            label.pack(side=tk.LEFT, padx=6)
            self._computed(lambda c=cat, l=label: self._limit_label(l, c))
        self._caption(line2, "CARGA").pack(side=tk.LEFT, padx=(16, 4))
        load = ctk.CTkLabel(line2, text="", font=ctk.CTkFont(size=12, weight="bold"))
        load.pack(side=tk.LEFT)
        self._computed(lambda: load.configure(
            text=f"{ordem.espacos_usados(self.sheet)} / {self.sheet['inventario']['carga_max']}",
            text_color=ERROR if ordem.sobrecarregado(self.sheet) else TEXT))

        self.items_view = ctk.CTkFrame(view, fg_color="transparent")
        self.items_view.pack(fill=tk.BOTH, expand=True)
        self._populate_items()

    def _limit_label(self, label, cat):
        used = ordem.itens_por_categoria(self.sheet)[cat]
        limit = self.sheet["inventario"]["limite_itens"][cat]
        label.configure(text=f"{cat}: {used}/{limit}", text_color=ERROR if used > limit else TEXT)

    def _populate_items(self):
        view = self.items_view
        for child in view.winfo_children():
            child.destroy()
        keys = ("nome", "categoria", "espacos")
        path = ("inventario", "itens")

        def add(es):
            item = {"nome": es[0].get().strip(), "categoria": es[1].get().strip().upper(),
                    "espacos": max(0, to_int(es[2].get(), 1))}
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
