"""Tela da ficha de Ordem Paranormal (mesma interface do mestre, do jogador e do modo offline).

A mecânica dos campos editáveis fica em src/ui/sheet_base.py; aqui ficam a disposição da ficha e as
regras do livro (src/ordem.apply_rules), reaplicadas a cada edição.
"""
import tkinter as tk

import customtkinter as ctk

from src import ordem
from src.sheet_io import to_int
from src.ui.common import (BUTTON, BUTTON_HOVER, ERROR, INPUT, PANEL, PANEL_DARK, TEXT, TEXT_DIM, TEXT_FAINT,
                           TEXT_MUTED, WARN, TabBar, fmt_bonus, small_button, update, update_bar)
from src.ui.sheet_base import BaseSheetView

SYSTEM = ordem.SYSTEM
RESOURCE_COLORS = {"pv": "#c0392b", "pe": "#d4a017", "san": "#2e86c1"}
TABS = ["Perícias", "Ataques", "Habilidades", "Rituais", "Inventário", "Descrição"]
CIRCULOS = [f"{c}º" for c in ordem.CUSTO_CIRCULO]
CLASS_NAMES = [c["nome"] for c in ordem.CLASSES.values()]
GRADE_LABELS = {value: label for value, label in ordem.GRAUS}
GRADE_VALUES = {label: value for value, label in ordem.GRAUS}
NONE = "—"


class SheetView(BaseSheetView):
    """Ficha de agente: regras do livro aplicadas por src/ordem.apply_rules."""
    apply_rules = staticmethod(ordem.apply_rules)

    def _needs_rebuild(self):
        # classe nova troca PV/PE/SAN manuais por calculados (ou o contrário)
        return ordem.class_key(self.sheet) != self._built_class

    @staticmethod
    def _roll_variant(req, variant):
        """Shift+clique = +1d20, Ctrl+clique = −1d20 (o "+O"/"−O" do livro). Com 0 dados, rola 2 e fica com o pior."""
        n_dados = {"vantagem": req.get("extra", 0) + 1, "desvantagem": 0}.get(req.get("mode"), 1)
        n_dados = max(0, n_dados + (1 if variant == "mais" else -1))
        sinal = "+" if variant == "mais" else "−"
        return ordem.teste_request(n_dados, req.get("bonus", 0), f"{req.get('label', '')} ({sinal}1 dado)".strip())

    @staticmethod
    def _display(value, kind):
        if kind == "grade":
            return GRADE_LABELS.get(value, GRADE_LABELS[0])
        if kind == "trilha":
            return ordem.TRILHA[value][1] if value in ordem.TRILHA else NONE
        if kind == "afinidade":
            return value or NONE
        return BaseSheetView._display(value, kind)

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
        if len(old.get("rituais", [])) != len(new_sheet.get("rituais", [])):
            self._populate_rituals()
        if len(old.get("inventario", {}).get("itens", [])) != len(new_sheet.get("inventario", {}).get("itens", [])):
            self._populate_items()
        self._sync_fields()
        self._refresh_computed()

    def _grade(self, parent, path):
        """Menu do grau de treinamento (Destreinado/Treinado/Veterano/Expert)."""
        menu = ctk.CTkOptionMenu(parent, values=list(GRADE_VALUES), width=104, height=22, fg_color=INPUT,
                                 button_color=BUTTON, button_hover_color=BUTTON_HOVER, font=ctk.CTkFont(size=10),
                                 dropdown_font=ctk.CTkFont(size=11),
                                 command=lambda label: self._commit(path, GRADE_VALUES[label]))
        self._write(menu, self._get(path), "grade")
        self.fields.append((menu, path, "grade"))
        return menu

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
        self._computed(lambda: update(self.lbl_title, 
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
        self._computed(lambda: update(origin_info, text=self._origin_text()))
        self._caption(grid, "CLASSE").grid(row=2, column=0, sticky="w", pady=3, padx=(0, 8))
        self._combo(grid, ("classe",), CLASS_NAMES).grid(row=2, column=1, sticky="ew", pady=3)
        if self._built_class is not None:
            self._build_trail(grid, 3)

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

    def _build_trail(self, grid, row):
        """Trilha da classe (p. 26-35) com as habilidades por NEX, e afinidade (NEX 50%, p. 114)."""
        trilhas = ordem.trilhas_da_classe(self.sheet)
        por_nome = {nome: key for key, nome, *_ in trilhas}
        self._caption(grid, "TRILHA").grid(row=row, column=0, sticky="w", pady=3, padx=(0, 8))
        self._option(grid, ("trilha",), [NONE] + list(por_nome), width=200, kind="trilha",
                     parse=lambda nome: por_nome.get(nome, "")).grid(row=row, column=1, sticky="ew", pady=3)

        powers = ctk.CTkFrame(grid, fg_color="transparent")
        powers.grid(row=row + 1, column=1, sticky="ew", pady=(0, 4))
        for n in range(len(ordem.NEX_TRILHA)):
            label = ctk.CTkLabel(powers, text="", font=ctk.CTkFont(size=10), anchor="w", justify=tk.LEFT,
                                 wraplength=280, height=16)
            label.pack(fill=tk.X)
            self._computed(lambda n=n, lbl=label: update(lbl, **self._trail_line(n)))

        self._caption(grid, "AFINIDADE").grid(row=row + 2, column=0, sticky="w", pady=3, padx=(0, 8))
        line = ctk.CTkFrame(grid, fg_color="transparent")
        line.grid(row=row + 2, column=1, sticky="ew", pady=3)
        menu = self._option(line, ("afinidade",), [NONE] + ordem.AFINIDADES, width=130, kind="afinidade",
                            parse=lambda nome: "" if nome == NONE else nome)
        menu.pack(side=tk.LEFT)
        note = ctk.CTkLabel(line, text="", font=ctk.CTkFont(size=9, slant="italic"), text_color=TEXT_FAINT)
        note.pack(side=tk.LEFT, padx=8)

        def show_affinity():
            liberada = self.sheet.get("nex", 5) >= ordem.NEX_AFINIDADE or self.sheet.get("afinidade")
            update(menu, state="normal" if liberada else "disabled")
            update(note, text="" if liberada else f"a partir de NEX {ordem.NEX_AFINIDADE}%")
        self._computed(show_affinity)

    def _trail_line(self, n):
        """Uma habilidade da trilha: em branco se já tem pelo NEX, apagada se ainda não."""
        linhas = ordem.habilidades_trilha(self.sheet)
        if n >= len(linhas):
            return {"text": "", "height": 1}
        nex, nome, tem, auto = linhas[n]
        pagina = ordem.TRILHA[self.sheet["trilha"]][2]
        text = f"NEX {nex}%  {nome}" + (f"  ·  {auto}" if auto and tem else "") + (f"  (p. {pagina})" if n == 0 else "")
        return {"text": text, "height": 16, "text_color": TEXT if tem else TEXT_FAINT}

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
        self._build_conditions(card)

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
        if key == "pv":
            hurt = ctk.CTkLabel(top, text="", font=ctk.CTkFont(size=10, weight="bold"))
            hurt.pack(side=tk.LEFT)
            self._computed(lambda: update(hurt, **self._pv_state_text()))

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
        self._computed(lambda k=key, b=bar: update_bar(b, self.sheet[k]["atual"] / max(1, self.sheet[k]["max"])))

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
        if key == "pv":
            self._dying_row(frame, "morrendo", "MORRENDO", "MORTO", "Estabilizar", ordem.estabilizar,
                            "Medicina DT 20 (+5 por vez na cena): fica com 1 PV")
        elif key == "san":
            self._dying_row(frame, "enlouquecendo", "ENLOUQUECENDO", "INSANO", "Acalmar", ordem.acalmar,
                            "Diplomacia ou Religião DT 20 (+5 por vez na cena): fica com SAN 1")

    # ----------------------------------------------------------------- condições (p. 310-311)
    CONDITION_HINT = "Passe o mouse numa condição para ver o efeito. Acabam no fim da cena."
    CONDITIONS_PER_ROW = 3

    def _build_conditions(self, parent):
        """Etiquetas das condições: o menu adiciona (repetir piora: abalado -> apavorado), o × tira."""
        frame = ctk.CTkFrame(parent, fg_color=PANEL_DARK, corner_radius=8)
        frame.pack(fill=tk.X, padx=12, pady=(6, 10))
        head = ctk.CTkFrame(frame, fg_color="transparent")
        head.pack(fill=tk.X, padx=10, pady=(6, 4))
        self._caption(head, "CONDIÇÕES").pack(side=tk.LEFT)
        add = ctk.CTkOptionMenu(head, values=[nome for _, nome, *_ in ordem.CONDICOES], width=120, height=22,
                                fg_color=BUTTON, button_color=BUTTON, button_hover_color=BUTTON_HOVER,
                                font=ctk.CTkFont(size=10), dropdown_font=ctk.CTkFont(size=11),
                                command=lambda nome: self._add_condition(nome, add))
        add.set("+ condição")
        add.pack(side=tk.RIGHT)
        chips = ctk.CTkFrame(frame, fg_color="transparent")
        chips.pack(fill=tk.X, padx=8)
        for col in range(self.CONDITIONS_PER_ROW):
            chips.grid_columnconfigure(col, weight=1, uniform="condicao")
        hint = ctk.CTkLabel(frame, text="", font=ctk.CTkFont(size=9, slant="italic"), text_color=TEXT_FAINT,
                            wraplength=330, justify="left", anchor="w")
        state = {"shown": None}

        def refresh():
            if not chips.winfo_exists():
                raise tk.TclError("ficha refeita")
            atuais = list(self.sheet.get("condicoes", []))
            if atuais == state["shown"]:
                return
            state["shown"] = atuais
            for child in chips.winfo_children():
                child.destroy()
            for n, key in enumerate(atuais):
                nome, resumo, _ = ordem.CONDICAO[key]
                chip = ctk.CTkFrame(chips, fg_color=PANEL, corner_radius=6, height=22)
                chip.grid(row=n // self.CONDITIONS_PER_ROW, column=n % self.CONDITIONS_PER_ROW, sticky="ew",
                          padx=2, pady=2)
                label = ctk.CTkLabel(chip, text=nome, font=ctk.CTkFont(size=10, weight="bold"), text_color=WARN,
                                     height=20)
                label.pack(side=tk.LEFT, padx=(6, 0))
                ctk.CTkButton(chip, text="×", width=16, height=18, fg_color="transparent", hover_color=BUTTON,
                              text_color=TEXT_MUTED, font=ctk.CTkFont(size=12),
                              command=lambda k=key: self._remove_condition(k)).pack(side=tk.RIGHT, padx=2)
                for widget in (chip, label):
                    widget.bind("<Enter>", lambda _e, t=f"{nome}: {resumo}": hint.configure(text=t))
                    widget.bind("<Leave>", lambda _e: hint.configure(text=self.CONDITION_HINT))
            hint.configure(text=self.CONDITION_HINT)
            if atuais:
                hint.pack(fill=tk.X, padx=10, pady=(2, 6))
            else:
                hint.pack_forget()

        self._computed(refresh)

    def _add_condition(self, nome, menu):
        menu.set("+ condição")
        key = next(k for k, n, *_ in ordem.CONDICOES if n == nome)
        ordem.adicionar_condicao(self.sheet, key)
        self._changed()

    def _remove_condition(self, key):
        ordem.remover_condicao(self.sheet, key)
        self._changed()

    def _defense_warning(self):
        lines = []
        if ordem.sobrecarregado(self.sheet):
            lines.append("Sobrecarregado: −5 na Defesa e nas perícias de carga, −3m de deslocamento")
        menos, nomes = ordem.penalidade_defesa(self.sheet)
        if menos:
            lines.append(f"Condições: −{menos} na Defesa ({', '.join(nomes)})")
        if "caido" in self.sheet.get("condicoes", []):
            lines.append("Caído: −5 na Defesa contra corpo a corpo, +5 contra à distância")
        return "\n".join(lines)

    def _pv_state_text(self):
        if ordem.inconsciente(self.sheet):
            return {"text": "INCONSCIENTE", "text_color": ERROR}
        if ordem.machucado_agente(self.sheet):
            return {"text": "MACHUCADO", "text_color": WARN}
        return {"text": "", "text_color": TEXT_FAINT}

    def _dying_row(self, parent, state, title, final, action_text, action, hint):
        """Morrendo/enlouquecendo (p. 88 e 111): só aparece quando ativo. As bolinhas contam os turnos
        iniciados assim na cena; a terceira é morte/insanidade."""
        row = ctk.CTkFrame(parent, fg_color=PANEL, corner_radius=6)
        turns = f"turnos_{state}"
        line = ctk.CTkFrame(row, fg_color="transparent")
        line.pack(fill=tk.X, padx=8, pady=(6, 0))
        label = ctk.CTkLabel(line, text=title, font=ctk.CTkFont(size=11, weight="bold"), text_color=ERROR)
        label.pack(side=tk.LEFT, padx=(0, 6))
        self._computed(lambda: update(label, text=final if self.sheet["estados"][turns] >= ordem.TURNOS_FATAIS
                                      else title))
        for n in range(1, ordem.TURNOS_FATAIS + 1):
            dot = ctk.CTkButton(line, text="", width=16, height=20, fg_color="transparent", hover_color=PANEL_DARK,
                                font=ctk.CTkFont(size=14),
                                command=lambda n=n: self._commit(("estados", turns),
                                                                 n - 1 if self.sheet["estados"][turns] == n else n))
            dot.pack(side=tk.LEFT)
            self._computed(lambda d=dot, n=n: update(
                d, text="●" if self.sheet["estados"][turns] >= n else "○",
                text_color=ERROR if self.sheet["estados"][turns] >= n else "#555555"))
        ctk.CTkLabel(line, text="turnos", font=ctk.CTkFont(size=9), text_color=TEXT_MUTED).pack(side=tk.LEFT, padx=4)
        small_button(line, action_text, lambda: self._state_action(action), width=70, height=20).pack(
            side=tk.RIGHT)
        small_button(line, "Nova cena", self._new_scene, width=64, height=20).pack(side=tk.RIGHT, padx=4)
        ctk.CTkLabel(row, text=hint, font=ctk.CTkFont(size=9, slant="italic"), text_color=TEXT_FAINT).pack(
            anchor=tk.W, padx=8, pady=(0, 6))
        shown = {"value": None}

        def show():
            visible = self.sheet["estados"][state] or self.sheet["estados"][turns] >= ordem.TURNOS_FATAIS
            if visible != shown["value"]:
                shown["value"] = visible
                if visible:
                    row.pack(fill=tk.X, padx=10, pady=(0, 8))
                else:
                    row.pack_forget()
        self._computed(show)

    def _state_action(self, action):
        action(self.sheet)
        self._changed()

    def _new_scene(self):
        ordem.nova_cena(self.sheet)
        self._changed()

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
        self._computed(lambda: update(agi, 
            text=f"= 10 + AGI ({self.sheet['atributos']['agi']})"
                 + (f" + {ordem.defesa_origem(self.sheet)} origem" if ordem.defesa_origem(self.sheet) else "") + " +"))
        for idx, (label, key) in enumerate((("Equip.", "equipamento"), ("Outros", "outros"))):
            col = ctk.CTkFrame(formula, fg_color="transparent")
            col.pack(side=tk.LEFT, padx=3)
            self._field(col, ("defesa", key), kind="int", width=40, justify="center").pack()
            ctk.CTkLabel(col, text=label, font=ctk.CTkFont(size=8), text_color=TEXT_FAINT).pack()
            if idx == 0:
                ctk.CTkLabel(formula, text="+", text_color=TEXT_DIM).pack(side=tk.LEFT)

        warn = ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=10, weight="bold"), text_color=ERROR,
                            wraplength=340, justify="left")
        warn.pack(anchor=tk.W, padx=12)
        self._computed(lambda: update(warn, text=self._defense_warning()))

        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(fill=tk.X, padx=12, pady=(4, 10))
        grid.grid_columnconfigure(1, weight=1)
        for r, (label, key, hint) in enumerate((("PROTEÇÃO", "protecao", "ex.: colete leve (+2 Defesa)"),
                                                 ("RESISTÊNCIAS", "resistencias", "ex.: balístico 5, perfuração 2"))):
            self._caption(grid, label).grid(row=r, column=0, sticky="nw", pady=(7, 3), padx=(0, 8))
            self._textbox(grid, (key,), framed=True, placeholder=hint).grid(row=r, column=1, sticky="ew", pady=3)

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
        self._build_rituals(views["Rituais"])
        self._build_inventory(views["Inventário"])
        self._build_description(views["Descrição"])
        self.tabs.switch(active_tab if active_tab in views else None)

    def _build_skills(self, view):
        head = ctk.CTkFrame(view, fg_color=PANEL_DARK, corner_radius=5)
        head.pack(fill=tk.X, pady=(0, 6))
        scroll = ctk.CTkScrollableFrame(view, fg_color=PANEL_DARK)
        scroll.pack(fill=tk.BOTH, expand=True)
        widths = (24, 200, 46, 56, 112, 56, 62)
        for col, (text, w) in enumerate(zip(("", "PERÍCIA", "ATRIB.", "DADOS", "TREINO", "OUTROS", "BÔNUS"), widths)):
            for frame in (head, scroll):
                frame.grid_columnconfigure(col, minsize=w, weight=1 if col == 1 else 0)
            self._caption(head, text).grid(row=0, column=col, sticky="w" if col == 1 else "", pady=5)

        for r, (key, nome, attr, so_treinada, carga) in enumerate(ordem.PERICIAS):
            marks = ("*" if so_treinada else "") + ("+" if carga else "")
            dot = ctk.CTkLabel(scroll, text="", font=ctk.CTkFont(size=13))
            dot.grid(row=r, column=0, pady=1)
            self._computed(lambda k=key, d=dot: update(d, 
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
            self._computed(lambda k=key, a=attr, d=dice: update(
                d, text=ordem.dados_pericia(self.sheet, k),
                text_color=WARN if ordem.penalidade_dados(self.sheet, k)[0] else TEXT_DIM))
            self._grade(scroll, ("pericias", key, "treino")).grid(row=r, column=4, pady=1)
            self._field(scroll, ("pericias", key, "outros"), kind="int", width=40, justify="center",
                        height=22).grid(row=r, column=5, pady=1)
            # o próprio bônus é o botão de rolar (não gasta coluna)
            self._bonus_button(
                scroll, lambda k=key: ordem.pericia_request(self.sheet, k),
                lambda k=key: fmt_bonus(ordem.bonus_pericia(self.sheet, k)),
                lambda k=key: ERROR if k in ordem.PERICIAS_CARGA and ordem.sobrecarregado(self.sheet) else TEXT,
            ).grid(row=r, column=6, pady=1)

        ctk.CTkLabel(view, text="+ Penalidade de carga.   * Somente treinada.   2d20↓ = 0 dados: rola 2d20 e fica com o "
                                "pior.   Dados em amarelo: condições tirando d20.",
                     font=ctk.CTkFont(size=9, slant="italic"), text_color=TEXT_FAINT).pack(anchor=tk.W, pady=(4, 0))

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
                        lambda i: self._remove(("ataques",), i, self._populate_attacks), wrap_key="especial",
                        placeholder="Crítico, alcance, efeito especial...", rolls=self._attack_rolls(("ataques",)),
                        affixes={"teste": ("Teste", None), "dano": ("Dano", None)})

    def _attack_rolls(self, items):
        """{"teste": f(idx), "dano": f(idx)}: pedidos de rolagem de um ataque (ou ação de ameaça)."""
        def item(idx):
            lista = self._get(items) or []
            return lista[idx] if idx < len(lista) else {}

        def teste(idx):
            it = item(idx)
            return ordem.ataque_request(self.sheet, it.get("teste"), it.get("nome") or "Ataque")

        def dano(idx):
            it = item(idx)
            return ordem.dano_request(it.get("dano"), f"{it.get('nome') or 'Ataque'} (dano)")

        return {"teste": teste, "dano": dano}

    # Habilidades & Rituais
    ABILITY_COLS = [(150, True), (40, False), (40, False), (170, True)]

    def _build_abilities(self, view):
        self.abilities_view = view
        self._populate_abilities()

    def _populate_abilities(self):
        view = self.abilities_view
        for child in view.winfo_children():
            child.destroy()
        keys = ("nome", "custo", "pagina", "descricao")
        scroll = self._list_section(
            view, self.ABILITY_COLS, ("Habilidade ou poder", "PE", "Pág.", "Descrição"),
            lambda es: self._append(("habilidades",), {k: e.get().strip() for k, e in zip(keys, es)}, es,
                                    self._populate_abilities))
        self._list_rows(scroll, ("habilidades",), self.sheet["habilidades"], self.ABILITY_COLS, keys,
                        lambda i: self._remove(("habilidades",), i, self._populate_abilities),
                        wrap_key="descricao", affixes={"custo": (None, "PE"), "pagina": ("Pág.", None)},
                        placeholder="Descrição da habilidade...")

    # Rituais (p. 118-121)
    RITUAL_ADD_COLS = [(160, True), (110, False), (60, False), (50, False)]
    RITUAL_DETAILS = (("execucao", "Execução", 80), ("alcance", "Alcance", 80), ("alvo", "Alvo/Área", 110),
                      ("duracao", "Duração", 90), ("resistencia", "Resistência", 110), ("dano", "Dano", 80))

    def _build_rituals(self, view):
        top = ctk.CTkFrame(view, fg_color="transparent")
        top.pack(fill=tk.X, pady=(0, 8))
        self._caption(top, "DT DE RITUAIS").pack(side=tk.LEFT, padx=(4, 8))
        self._value_label(top, lambda: ordem.dt_rituais(self.sheet), size=16).pack(side=tk.LEFT)
        dt_hint = ctk.CTkLabel(top, text="", font=ctk.CTkFont(size=10), text_color=TEXT_FAINT)
        dt_hint.pack(side=tk.LEFT, padx=10)
        self._computed(lambda: update(dt_hint, 
            text=f"= 10 + limite de PE ({ordem.limite_pe(self.sheet)}) + PRE ({self.sheet['atributos']['pre']})"))
        self.rituals_view = ctk.CTkFrame(view, fg_color="transparent")
        self.rituals_view.pack(fill=tk.BOTH, expand=True)
        self._populate_rituals()

    def _ritual(self, idx):
        rituais = self.sheet.get("rituais", [])
        return rituais[idx] if idx < len(rituais) else None

    def _populate_rituals(self):
        view = self.rituals_view
        for child in view.winfo_children():
            child.destroy()
        path = ("rituais",)

        def add(es):
            nome, elemento, circulo, pagina = (e.get().strip() for e in es)
            elemento = next((el for el in ordem.ELEMENTOS if el.lower() == elemento.lower()), "")
            self._append(path, {"nome": nome, "elemento": elemento, "circulo": max(1, min(to_int(circulo, 1), 4)),
                                "pagina": pagina, **{k: "" for k, *_ in self.RITUAL_DETAILS}, "descricao": ""},
                         es, self._populate_rituals)

        def dano(idx):
            ritual = self._ritual(idx)
            return ritual and ordem.dano_request(ritual["dano"], f"{ritual['nome'] or 'Ritual'} (dano)")

        def custo(idx, label):
            ritual = self._ritual(idx)
            if ritual is None or not label.winfo_exists():
                raise tk.TclError("ritual removido")  # sai da lista de calculados
            update(label, text=f"{ordem.custo_ritual(ritual)} PE")

        scroll = self._list_section(view, self.RITUAL_ADD_COLS, ("Ritual", "Elemento", "Círculo", "Pág."), add)
        for idx in range(len(self.sheet["rituais"])):
            base = path + (idx,)
            row = ctk.CTkFrame(scroll, fg_color=PANEL)
            row.pack(fill=tk.X, pady=3, padx=4)
            line = ctk.CTkFrame(row, fg_color="transparent")
            line.pack(fill=tk.X)
            # da direita para a esquerda: X, página, custo, círculo, elemento; o nome ocupa o resto
            small_button(line, "X", lambda i=idx: self._remove(path, i, self._populate_rituals), width=24,
                         danger=True, height=20).pack(side=tk.RIGHT, padx=8)
            self._field(line, base + ("pagina",), width=36, transparent=True).pack(side=tk.RIGHT)
            ctk.CTkLabel(line, text="Pág.", font=ctk.CTkFont(size=10), text_color=TEXT_MUTED).pack(
                side=tk.RIGHT, padx=(10, 0))
            cost = ctk.CTkLabel(line, text="", width=44, font=ctk.CTkFont(size=11, weight="bold"), text_color=TEXT)
            cost.pack(side=tk.RIGHT)
            self._computed(lambda i=idx, c=cost: custo(i, c))
            self._option(line, base + ("circulo",), CIRCULOS, width=56, kind="circulo",
                         parse=lambda label: int(label[0])).pack(side=tk.RIGHT, padx=3)
            self._option(line, base + ("elemento",), ordem.ELEMENTOS, width=118).pack(side=tk.RIGHT, padx=3)
            self._field(line, base + ("nome",), width=150, transparent=True, bold=True, size=12,
                        text_color=self.color).pack(side=tk.LEFT, padx=3, pady=3, fill=tk.X, expand=True)

            details = ctk.CTkFrame(row, fg_color="transparent")
            details.pack(fill=tk.X, padx=3)
            for col in range(3):
                details.grid_columnconfigure(col, weight=1, uniform="ritual")
            for n, (key, label, width) in enumerate(self.RITUAL_DETAILS):
                cell = details if key != "dano" else ctk.CTkFrame(details, fg_color="transparent")
                entry = self._field(cell, base + (key,), width=width, placeholder=label, size=10, height=22)
                if key == "dano":
                    self._roll_button(cell, lambda i=idx: dano(i)).pack(side=tk.RIGHT, padx=(2, 0))
                    entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
                    entry = cell
                entry.grid(row=n // 3, column=n % 3, sticky="ew", padx=2, pady=1)
            self._textbox(row, base + ("descricao",), auto_height=True, text_color=TEXT_DIM,
                          placeholder="Efeito do ritual, formas discente e verdadeira...").pack(
                fill=tk.X, padx=6, pady=(0, 6))

    # Inventário
    ITEM_COLS = [(140, True), (70, False), (60, False), (140, True)]

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
        self._computed(lambda: update(load, 
            text=f"{ordem.espacos_usados(self.sheet)} / {self.sheet['inventario']['carga_max']}"
                 f"  (máx. {ordem.carga_absoluta(self.sheet)})",
            text_color=ERROR if ordem.sobrecarregado(self.sheet) else TEXT))
        self.inv_msg = ctk.CTkLabel(top, text="", font=ctk.CTkFont(size=10, weight="bold"), text_color=ERROR, height=0)
        self.inv_msg.pack(anchor=tk.W, padx=8)

        self.items_view = ctk.CTkFrame(view, fg_color="transparent")
        self.items_view.pack(fill=tk.BOTH, expand=True)
        self._populate_items()

    def _limit_label(self, label, cat):
        used = ordem.itens_por_categoria(self.sheet)[cat]
        limit = self.sheet["inventario"]["limite_itens"][cat]
        update(label, text=f"{cat}: {used}/{limit}", text_color=ERROR if used > limit else TEXT)

    def _populate_items(self):
        view = self.items_view
        for child in view.winfo_children():
            child.destroy()
        keys = ("nome", "categoria", "espacos", "descricao")
        path = ("inventario", "itens")

        def add(es):
            item = {"nome": es[0].get().strip(), "categoria": es[1].get().strip().upper(),
                    "espacos": max(0, to_int(es[2].get(), 1)), "descricao": es[3].get().strip()}
            livre = ordem.carga_absoluta(self.sheet) - ordem.espacos_usados(self.sheet)
            if item["nome"] and item["espacos"] > livre:
                self._inventory_warning(f"{item['nome']} não cabe: ocupa {item['espacos']} e só restam {max(0, livre)} "
                                        f"espaços até o dobro da carga ({ordem.carga_absoluta(self.sheet)}).")
                return
            self._inventory_warning("")
            self._append(path, item, es, self._populate_items)

        def clamp_espacos(idx, value):
            """Aumentar os espaços de um item não pode passar do dobro da carga."""
            itens = self.sheet["inventario"]["itens"]
            outros = ordem.espacos_usados(self.sheet) - itens[idx]["espacos"]
            limite = max(0, ordem.carga_absoluta(self.sheet) - outros)
            if value > limite:
                self._inventory_warning(f"Máximo de {limite} espaços para este item (dobro da carga: "
                                        f"{ordem.carga_absoluta(self.sheet)}).")
                return min(value, max(itens[idx]["espacos"], limite))  # pode manter ou reduzir, não aumentar
            self._inventory_warning("")
            return max(0, value)

        scroll = self._list_section(view, self.ITEM_COLS, ("Item", "Categoria", "Espaços", "Descrição"), add)
        self._list_rows(scroll, path, self.sheet["inventario"]["itens"], self.ITEM_COLS, keys,
                        lambda i: self._remove(path, i, self._populate_items), first_bold=False,
                        clamps={"espacos": clamp_espacos}, wrap_key="descricao",
                        placeholder="Descrição do item (o que faz, bônus...)")

    def _inventory_warning(self, text):
        try:
            update(self.inv_msg, text=text, height=18 if text else 0)
        except tk.TclError:
            pass

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
