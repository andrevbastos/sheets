"""Tela da ficha de D&D 5e (mesma interface do mestre, do jogador e do modo offline).

Tudo é editável no lugar. As regras do Livro do Jogador (src/dnd.apply_rules) recalculam
modificadores, bônus de proficiência, perícias, testes de resistência, iniciativa, Percepção
passiva e CD/bônus de magia a cada edição. A mecânica dos campos fica em src/ui/sheet_base.py.
"""
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from src import dnd
from src.sheet_io import to_int
from src.ui.common import (BUTTON, ERROR, OK, PANEL, PANEL_DARK, TEXT, TEXT_DIM, TEXT_FAINT, TEXT_MUTED, TITLE_FONT,
                           TabBar, fmt_bonus, small_button, update, update_bar)
from src.ui.sheet_base import BaseSheetView

SYSTEM = dnd.SYSTEM
TABS = ["Perícias", "Ataques", "Magias", "Traços", "Inventário", "Extra"]  # Traços = características e talentos
SIGLAS = {attr: sigla for attr, sigla, _ in dnd.ATRIBUTOS}
GRAU_LABELS = dict(dnd.GRAUS)
GRAU_VALUES = {label: value for value, label in dnd.GRAUS}
NO_ATTR = "—"
EXTRA_NAMES = {"cartas_destino": "Cartas de Destino"}
RECUPERA_LABELS = {"": NO_ATTR, "curto": "Curto", "longo": "Longo"}  # descanso em que o recurso volta
RECUPERA_VALUES = {label: value for value, label in RECUPERA_LABELS.items()}
NIVEIS_MAGIA = ["Truque"] + [f"{n}º nível" for n in range(1, 10)]


class SheetView(BaseSheetView):
    DEFAULT_COLOR = "#d4af37"
    apply_rules = staticmethod(dnd.apply_rules)

    def _needs_rebuild(self):
        # escolher/tirar o atributo de conjuração troca CD e bônus digitados por calculados
        return (dnd.atributo_conjuracao(self.sheet) is None) != self._built_manual_spells

    @staticmethod
    def _display(value, kind):
        if kind == "grau":
            return GRAU_LABELS.get(value, NO_ATTR)
        if kind == "atributo":
            return SIGLAS.get(value, NO_ATTR)
        if kind == "dado":
            return value or NO_ATTR
        if kind == "recupera":
            return RECUPERA_LABELS.get(value, NO_ATTR)
        if kind == "nivel_magia":
            return NIVEIS_MAGIA[value] if isinstance(value, int) and 0 <= value <= 9 else NIVEIS_MAGIA[0]
        return BaseSheetView._display(value, kind)

    # ================================================================= API
    def set_sheet(self, new_sheet: dict):
        if not new_sheet or new_sheet == self.sheet:
            return
        old, self.sheet = self.sheet, new_sheet
        if (old.get("cor") != new_sheet.get("cor") or set(old.get("extra", {})) != set(new_sheet.get("extra", {}))
                or (dnd.atributo_conjuracao(old) is None) != (dnd.atributo_conjuracao(new_sheet) is None)):
            self._rebuild()
            return
        for key, populate in (("ataques", self._populate_attacks), ("caracteristicas", self._populate_features),
                              ("inventario", self._populate_inventory)):
            if len(old.get(key, [])) != len(new_sheet.get(key, [])):
                populate()
        if len(old.get("recursos", [])) != len(new_sheet.get("recursos", [])):
            self._populate_resources()
        if [m["nivel"] for m in old["magias"]["lista"]] != [m["nivel"] for m in new_sheet["magias"]["lista"]]:
            self._populate_spell_list()
        if old.get("extra") != new_sheet.get("extra"):
            for key in new_sheet.get("extra", {}):
                self._populate_extra(key)
        self._sync_fields()
        self._refresh_computed()

    # ================================================================= construção
    def _build(self, active_tab=None):
        self.fields = []
        self.computed = []
        self._built_manual_spells = dnd.atributo_conjuracao(self.sheet) is None

        header = self._card(self, fill=tk.X, padx=10, pady=(5, 10))
        self._field(header, ("nome",), width=380, size=20, bold=True, transparent=True, text_color=self.color,
                    placeholder="Nome do personagem", height=36).pack(side=tk.LEFT, padx=14, pady=8)
        right = ctk.CTkFrame(header, fg_color="transparent")
        right.pack(side=tk.RIGHT, padx=14)
        self._caption(right, "JOGADOR").pack(side=tk.LEFT, padx=(0, 6))
        self._field(right, ("jogador",), width=160).pack(side=tk.LEFT)
        title = ctk.CTkLabel(right, text="", font=ctk.CTkFont(size=12), text_color=TEXT_DIM)
        title.pack(side=tk.LEFT, padx=(16, 0))
        self._computed(lambda: update(title, text=f"{self.sheet['classe'] or 'Sem classe'}  |  "
                                                  f"Nível {self.sheet['nivel']}"))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        left = ctk.CTkScrollableFrame(body, fg_color="transparent", width=380)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        right_col = ctk.CTkFrame(body, fg_color="transparent")
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self._build_attributes(left)
        self._build_identity(left)
        self._build_combat(left)
        self._build_saves(left)
        self._build_resources(left)
        self._build_tabs(right_col, active_tab)

    # ----------------------------------------------------------------- coluna esquerda
    def _build_attributes(self, parent):
        card = self._card(parent, "ATRIBUTOS", fill=tk.X, pady=(0, 10))
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill=tk.X, padx=8, pady=(0, 10))
        for idx, (attr, sigla, nome) in enumerate(dnd.ATRIBUTOS):
            row.grid_columnconfigure(idx, weight=1)
            box = ctk.CTkFrame(row, fg_color=PANEL_DARK, corner_radius=6)
            box.grid(row=0, column=idx, padx=2, sticky="nsew")
            self._caption(box, sigla).pack(pady=(5, 0))
            self._bonus_button(box, lambda a=attr: dnd.atributo_request(self.sheet, a),
                               lambda a=attr: fmt_bonus(dnd.mod(self.sheet, a)), width=50, size=15).pack(pady=2)
            self._field(box, ("atributos", attr, "valor"), kind="int", width=38, height=22, justify="center",
                        clamp=lambda v: max(1, min(v, 30))).pack(pady=(0, 6))

    def _build_identity(self, parent):
        card = self._card(parent, None, fill=tk.X, pady=(0, 10))
        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(fill=tk.X, padx=12, pady=(10, 4))
        for col in (1, 3):
            grid.grid_columnconfigure(col, weight=1)
        for n, (label, key, hint) in enumerate((("CLASSE", "classe", "Guerreiro"), ("RAÇA", "raca", "Humano"),
                                                ("ANTECED.", "antecedente", "Herói do Povo"),
                                                ("TENDÊNCIA", "tendencia", "Leal e Bom"))):
            r, c = divmod(n, 2)
            self._caption(grid, label).grid(row=r, column=c * 2, sticky="w", padx=(0 if c == 0 else 8, 6), pady=3)
            self._field(grid, (key,), width=100, placeholder=hint).grid(row=r, column=c * 2 + 1, sticky="ew", pady=3)

        small = ctk.CTkFrame(card, fg_color="transparent")
        small.pack(fill=tk.X, padx=12, pady=(4, 10))
        for idx in range(4):
            small.grid_columnconfigure(idx, weight=1)

        def box(idx, label):
            frame = ctk.CTkFrame(small, fg_color=PANEL_DARK, corner_radius=6)
            frame.grid(row=0, column=idx, padx=2, sticky="nsew")
            self._caption(frame, label).pack(pady=(5, 0))
            return frame

        self._field(box(0, "NÍVEL"), ("nivel",), kind="int", width=40, size=15, bold=True, justify="center",
                    transparent=True, clamp=lambda v: max(1, min(v, dnd.NIVEL_MAX))).pack(pady=(0, 4))
        self._field(box(1, "XP"), ("experiencia",), kind="int", width=64, size=13, justify="center",
                    transparent=True, clamp=lambda v: max(0, v)).pack(pady=(0, 4))
        self._value_label(box(2, "PROFICIÊNCIA"), lambda: fmt_bonus(dnd.prof(self.sheet))).pack(pady=(2, 6))
        self._value_label(box(3, "PERC. PASSIVA"), lambda: dnd.percepcao_passiva(self.sheet)).pack(pady=(2, 6))

    def _build_combat(self, parent):
        card = self._card(parent, None, fill=tk.X, pady=(0, 10))
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill=tk.X, padx=12, pady=(10, 4))
        for idx in range(4):
            top.grid_columnconfigure(idx, weight=1, uniform="combate")

        def box(idx, label):
            frame = ctk.CTkFrame(top, fg_color=PANEL_DARK, corner_radius=6)
            frame.grid(row=0, column=idx, padx=2, sticky="nsew")
            self._caption(frame, label).pack(pady=(5, 0))
            return frame

        self._field(box(0, "CA"), ("combate", "ca"), kind="int", width=44, size=18, bold=True, justify="center",
                    transparent=True).pack(pady=(0, 6))
        ini = box(1, "INICIATIVA")
        self._bonus_button(ini, lambda: dnd.iniciativa_request(self.sheet, "Iniciativa"),
                           lambda: fmt_bonus(dnd.iniciativa(self.sheet)), width=56, size=14).pack(pady=2)
        line = ctk.CTkFrame(ini, fg_color="transparent")
        line.pack(pady=(0, 6))
        ctk.CTkLabel(line, text="outros", font=ctk.CTkFont(size=9), text_color=TEXT_FAINT).pack(side=tk.LEFT, padx=2)
        self._field(line, ("combate", "iniciativa_outros"), kind="int", width=28, height=20,
                    justify="center").pack(side=tk.LEFT)
        self._field(box(2, "DESLOC."), ("combate", "deslocamento"), width=56, size=15, bold=True,
                    justify="center", transparent=True).pack(pady=(0, 6))
        # Inspiração (p. 125): tem ou não tem
        star = ctk.CTkButton(box(3, "INSPIRAÇÃO"), text="", width=40, height=30, fg_color="transparent",
                             hover_color=PANEL, font=ctk.CTkFont(size=22),
                             command=lambda: self._commit(("inspiracao",), not self.sheet["inspiracao"]))
        star.pack(pady=(0, 4))
        self._computed(lambda: update(star, text="★" if self.sheet["inspiracao"] else "☆",
                                      text_color=self.color if self.sheet["inspiracao"] else "#555555"))

        # Pontos de vida
        frame = ctk.CTkFrame(card, fg_color=PANEL_DARK, corner_radius=8)
        frame.pack(fill=tk.X, padx=12, pady=(6, 12))
        head = ctk.CTkFrame(frame, fg_color="transparent")
        head.pack(fill=tk.X, padx=10, pady=(6, 0))
        ctk.CTkLabel(head, text="PV", font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXT).pack(side=tk.LEFT)
        self._caption(head, "TEMP").pack(side=tk.LEFT, padx=(12, 4))
        self._field(head, ("combate", "hp_temp"), kind="int", width=36, justify="center",
                    clamp=lambda v: max(0, v)).pack(side=tk.LEFT)
        vals = ctk.CTkFrame(head, fg_color="transparent")
        vals.pack(side=tk.RIGHT)
        combate = ("combate",)
        self._field(vals, combate + ("hp_atual",), kind="int", width=48, size=16, bold=True, justify="center",
                    clamp=lambda v: max(0, min(v, self.sheet["combate"]["hp_max"]))).pack(side=tk.LEFT)
        ctk.CTkLabel(vals, text="/", font=ctk.CTkFont(size=16), text_color=TEXT_MUTED).pack(side=tk.LEFT, padx=4)
        self._field(vals, combate + ("hp_max",), kind="int", width=48, size=16, justify="center",
                    clamp=lambda v: max(0, v)).pack(side=tk.LEFT)
        bar = ctk.CTkProgressBar(frame, fg_color=BUTTON, height=8)
        bar.pack(fill=tk.X, padx=10, pady=6)

        def show_hp():
            c = self.sheet["combate"]
            ratio = c["hp_atual"] / max(1, c["hp_max"])
            update_bar(bar, ratio)
            update(bar, progress_color=OK if ratio > 0.3 else ERROR)  # verde; vermelho com 30% ou menos
        self._computed(show_hp)

        # dano e cura: botões rápidos ou um valor digitado (o dano tira primeiro os PV temporários)
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

        # dados de vida (p. 186): gastar um rola o dado + CON
        dv = ctk.CTkFrame(frame, fg_color="transparent")
        dv.pack(fill=tk.X, padx=10, pady=(0, 8))
        self._caption(dv, "DADOS DE VIDA").pack(side=tk.LEFT)
        self._option(dv, ("combate", "dados_vida", "dado"), [NO_ATTR] + dnd.DADOS_VIDA, width=64, kind="dado",
                     parse=lambda label: "" if label == NO_ATTR else label).pack(side=tk.LEFT, padx=6)
        self._field(dv, ("combate", "dados_vida", "restantes"), kind="int", width=30, height=22, justify="center",
                    clamp=lambda v: max(0, min(v, self.sheet["nivel"]))).pack(side=tk.LEFT)
        total = ctk.CTkLabel(dv, text="", font=ctk.CTkFont(size=11), text_color=TEXT_MUTED)
        total.pack(side=tk.LEFT, padx=(3, 6))
        self._computed(lambda: update(total, text=f"/ {self.sheet['nivel']}"))
        self._roll_button(dv, self._spend_hit_die_request, text="Gastar", width=70).pack(side=tk.LEFT)

        # testes contra a morte (p. 197): só aparecem com 0 PV
        death = ctk.CTkFrame(frame, fg_color=PANEL, corner_radius=6)
        state = {"shown": None}
        self._caption(death, "MORTE").pack(side=tk.LEFT, padx=(8, 6), pady=6)
        for key, label, color in (("sucessos", "sucessos", OK), ("falhas", "falhas", ERROR)):
            for n in range(1, 4):
                dot = ctk.CTkButton(death, text="", width=16, height=20, fg_color="transparent", hover_color=PANEL_DARK,
                                    font=ctk.CTkFont(size=14),
                                    command=lambda k=key, n=n: self._commit(
                                        ("combate", "morte", k), n - 1 if self.sheet["combate"]["morte"][k] == n else n))
                dot.pack(side=tk.LEFT)
                self._computed(lambda d=dot, k=key, n=n, col=color: update(
                    d, text="●" if self.sheet["combate"]["morte"][k] >= n else "○",
                    text_color=col if self.sheet["combate"]["morte"][k] >= n else "#555555"))
            ctk.CTkLabel(death, text=label, font=ctk.CTkFont(size=9), text_color=TEXT_MUTED).pack(
                side=tk.LEFT, padx=(2, 8))
        self._roll_button(death, lambda: dnd.morte_request(self.sheet)).pack(side=tk.RIGHT, padx=6)

        def show_death():
            c = self.sheet["combate"]
            visible = c["hp_atual"] == 0 and c["hp_max"] > 0
            if visible != state["shown"]:
                state["shown"] = visible
                if visible:
                    death.pack(fill=tk.X, padx=10, pady=(0, 8))
                else:
                    death.pack_forget()
        self._computed(show_death)

    def _hp_change(self, delta):
        if delta < 0:
            dnd.sofrer_dano(self.sheet, -delta)
        else:
            dnd.curar(self.sheet, delta)
        self._changed()

    def _hp_from_entry(self, entry, sign):
        valor = max(0, to_int(entry.get(), 0))
        entry.delete(0, tk.END)
        self.winfo_toplevel().focus()
        if valor:
            self._hp_change(sign * valor)

    def _spend_hit_die_request(self):
        """O botão rola o dado de vida e já desconta um dos restantes."""
        req = dnd.dado_vida_request(self.sheet)
        if req is None:
            return None
        return {**req, "_on_roll": self._spend_hit_die}

    def _spend_hit_die(self):
        dv = self.sheet["combate"]["dados_vida"]
        if dv["restantes"] > 0:
            dv["restantes"] -= 1
            self._changed()

    # ----------------------------------------------------------------- recursos e descanso (p. 186)
    def _build_resources(self, parent):
        card = self._card(parent, None, fill=tk.X, pady=(0, 10))
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill=tk.X, padx=12, pady=(8, 4))
        ctk.CTkLabel(head, text="RECURSOS", font=ctk.CTkFont(family=TITLE_FONT, size=13, weight="bold"),
                     text_color=TEXT).pack(side=tk.LEFT)
        small_button(head, "Descanso longo", self._long_rest, width=96).pack(side=tk.RIGHT, padx=2)
        small_button(head, "Descanso curto", self._short_rest, width=96).pack(side=tk.RIGHT, padx=2)
        self.resources_view = ctk.CTkFrame(card, fg_color="transparent")
        self.resources_view.pack(fill=tk.X, padx=8)

        add = ctk.CTkFrame(card, fg_color="transparent")
        add.pack(fill=tk.X, padx=12, pady=(4, 10))
        name = ctk.CTkEntry(add, height=24, placeholder_text="Novo recurso (ex.: Fúria)", font=ctk.CTkFont(size=11))
        name.pack(side=tk.LEFT, fill=tk.X, expand=True)
        maximum = ctk.CTkEntry(add, width=44, height=24, placeholder_text="máx.", justify="center",
                               font=ctk.CTkFont(size=11))
        maximum.pack(side=tk.LEFT, padx=4)

        def add_resource():
            nome = name.get().strip()
            if not nome:
                return
            valor = max(0, to_int(maximum.get(), 1))
            self.sheet["recursos"].append({"nome": nome, "atual": valor, "max": valor, "recupera": "longo",
                                           "detalhes": ""})
            name.delete(0, tk.END)
            maximum.delete(0, tk.END)
            self._populate_resources()
            self._changed()

        small_button(add, "Adicionar", add_resource, width=70, height=24).pack(side=tk.LEFT)
        for entry in (name, maximum):
            entry.bind("<Return>", lambda *_: add_resource())
        self._populate_resources()

    def _populate_resources(self):
        view = self.resources_view
        for child in view.winfo_children():
            child.destroy()
        path = ("recursos",)
        for idx in range(len(self.sheet["recursos"])):
            base = path + (idx,)
            row = ctk.CTkFrame(view, fg_color=PANEL_DARK, corner_radius=6)
            row.pack(fill=tk.X, pady=2)
            line = ctk.CTkFrame(row, fg_color="transparent")
            line.pack(fill=tk.X)
            small_button(line, "X", lambda i=idx: self._remove(path, i, self._populate_resources), width=20,
                         danger=True, height=20).pack(side=tk.RIGHT, padx=(2, 6))
            self._option(line, base + ("recupera",), list(RECUPERA_LABELS.values()), width=64, kind="recupera",
                         parse=lambda label: RECUPERA_VALUES[label]).pack(side=tk.RIGHT, padx=2)
            small_button(line, "+", lambda i=idx: self._resource_step(i, 1), width=20, height=20).pack(
                side=tk.RIGHT, padx=1)
            self._field(line, base + ("max",), kind="int", width=26, height=20, size=10, justify="center",
                        transparent=True, clamp=lambda v: max(0, v)).pack(side=tk.RIGHT)
            ctk.CTkLabel(line, text="/", text_color=TEXT_MUTED, width=6).pack(side=tk.RIGHT)
            self._field(line, base + ("atual",), kind="int", width=26, height=20, size=11, bold=True,
                        justify="center", clamp=lambda v, i=idx: max(0, min(v, self.sheet["recursos"][i]["max"]))
                        ).pack(side=tk.RIGHT)
            small_button(line, "−", lambda i=idx: self._resource_step(i, -1), width=20, height=20).pack(
                side=tk.RIGHT, padx=1)
            self._field(line, base + ("nome",), width=80, transparent=True, bold=True, size=11,
                        text_color=self.color).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2, pady=2)
            self._textbox(row, base + ("detalhes",), auto_height=True, text_color=TEXT_DIM,
                          placeholder="O que faz...").pack(fill=tk.X, padx=4, pady=(0, 4))

    def _resource_step(self, idx, delta):
        r = self.sheet["recursos"][idx]
        value = max(0, min(r["atual"] + delta, r["max"]))
        if value != r["atual"]:
            r["atual"] = value
            self._changed()

    def _short_rest(self):
        dnd.descanso_curto(self.sheet)
        self._changed()

    def _long_rest(self):
        if not messagebox.askyesno("Descanso longo", "Recuperar todos os PV, metade dos dados de vida, os espaços "
                                   "de magia e os recursos?", parent=self.winfo_toplevel()):
            return
        if not dnd.descanso_longo(self.sheet):
            messagebox.showinfo("Descanso longo", "Com 0 PV não dá para descansar: é preciso ter pelo menos 1 PV "
                                "no início do descanso (p. 186).", parent=self.winfo_toplevel())
            return
        self._changed()

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
        self._build_spells(views["Magias"])
        self._build_features(views["Traços"])
        self.inventory_view = views["Inventário"]
        self._populate_inventory()
        self._build_extra(views["Extra"])
        self.tabs.switch(active_tab if active_tab in views else None)

    def _table(self, view, headers, widths):
        head = ctk.CTkFrame(view, fg_color=PANEL_DARK, corner_radius=5)
        head.pack(fill=tk.X, pady=(0, 6))
        scroll = ctk.CTkScrollableFrame(view, fg_color=PANEL_DARK)
        scroll.pack(fill=tk.BOTH, expand=True)
        for col, (text, w) in enumerate(zip(headers, widths)):
            for frame in (head, scroll):
                frame.grid_columnconfigure(col, minsize=w, weight=1 if col == 1 else 0)
            self._caption(head, text).grid(row=0, column=col, sticky="w" if col == 1 else "", pady=5)
        return scroll

    def _dot(self, parent, row, is_on):
        dot = ctk.CTkLabel(parent, text="", font=ctk.CTkFont(size=13))
        dot.grid(row=row, column=0, pady=1)
        self._computed(lambda: update(dot, text="●" if is_on() else "○",
                                      text_color=self.color if is_on() else "#444444"))


    def _build_skills(self, view):
        scroll = self._table(view, ("", "PERÍCIA", "ATRIB.", "PROFICIÊNCIA", "OUTROS", "BÔNUS"),
                             (24, 200, 46, 120, 56, 62))
        for r, (key, nome, attr) in enumerate(dnd.PERICIAS):
            self._dot(scroll, r, lambda k=key: self.sheet["pericias"][k]["grau"] > 0)
            ctk.CTkLabel(scroll, text=nome.upper(), font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=TEXT).grid(row=r, column=1, sticky="w")
            ctk.CTkLabel(scroll, text=SIGLAS[attr], font=ctk.CTkFont(size=10), text_color=TEXT_MUTED).grid(
                row=r, column=2)
            self._option(scroll, ("pericias", key, "grau"), list(GRAU_VALUES), width=112, kind="grau",
                         parse=lambda label: GRAU_VALUES[label]).grid(row=r, column=3, pady=1)
            self._field(scroll, ("pericias", key, "outros"), kind="int", width=40, justify="center",
                        height=22).grid(row=r, column=4, pady=1)
            self._bonus_button(scroll, lambda k=key: dnd.pericia_request(self.sheet, k),
                               lambda k=key: fmt_bonus(dnd.bonus_pericia(self.sheet, k))).grid(row=r, column=5, pady=1)
        ctk.CTkLabel(view, text="Bônus = atributo + proficiência (dobrada se especialista) + outros.   "
                                "Clique no bônus para rolar: Shift = vantagem, Ctrl = desvantagem.",
                     font=ctk.CTkFont(size=9, slant="italic"), text_color=TEXT_FAINT).pack(anchor=tk.W, pady=(4, 0))

    def _build_saves(self, parent):
        """Cartão na coluna da esquerda: 3 linhas × 2 colunas. A bolinha marca/desmarca a proficiência."""
        card = self._card(parent, "TESTES DE RESISTÊNCIA", fill=tk.X, pady=(0, 10))
        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(fill=tk.X, padx=10, pady=(0, 8))
        for col in (1, 5):
            grid.grid_columnconfigure(col, weight=1)
        for n, (attr, sigla, nome) in enumerate(dnd.ATRIBUTOS):
            r, c = n % 3, (n // 3) * 4
            path = ("resistencia", attr, "proficiente")
            dot = ctk.CTkButton(grid, text="", width=20, height=20, fg_color="transparent", hover_color=PANEL_DARK,
                                font=ctk.CTkFont(size=14),
                                command=lambda p=path: self._commit(p, not self._get(p)))
            dot.grid(row=r, column=c, pady=1)
            self._computed(lambda d=dot, p=path: update(d, text="●" if self._get(p) else "○",
                                                         text_color=self.color if self._get(p) else "#555555"))
            ctk.CTkLabel(grid, text=sigla, font=ctk.CTkFont(size=11, weight="bold"), text_color=TEXT,
                         anchor="w").grid(row=r, column=c + 1, sticky="w")
            self._field(grid, ("resistencia", attr, "outros"), kind="int", width=28, height=20, size=10,
                        justify="center", placeholder="0").grid(row=r, column=c + 2, padx=2)
            self._bonus_button(grid, lambda a=attr: dnd.resistencia_request(self.sheet, a),
                               lambda a=attr: fmt_bonus(dnd.bonus_resistencia(self.sheet, a)), width=50,
                               size=11).grid(row=r, column=c + 3, pady=1)
        ctk.CTkLabel(card, text="● = proficiente (clique para trocar). O campo pequeno soma outros bônus.",
                     font=ctk.CTkFont(size=9, slant="italic"), text_color=TEXT_FAINT).pack(anchor=tk.W, padx=12,
                                                                                         pady=(0, 8))

    # Ataques
    ATTACK_COLS = [(140, True), (72, False), (110, False), (140, True)]

    def _populate_attacks(self):
        view = self.attacks_view
        for child in view.winfo_children():
            child.destroy()
        keys, path = ("nome", "ataque", "dano", "descricao"), ("ataques",)
        scroll = self._list_section(
            view, self.ATTACK_COLS, ("Arma ou ataque", "+5 ou FOR", "1d8+FOR", "Alcance, propriedades..."),
            lambda es: self._append(path, {k: e.get().strip() for k, e in zip(keys, es)}, es,
                                    self._populate_attacks))

        def item(idx):
            lista = self.sheet["ataques"]
            return lista[idx] if idx < len(lista) else {}

        rolls = {"ataque": lambda i: dnd.ataque_request(self.sheet, item(i).get("ataque"), item(i).get("nome") or "Ataque"),
                 "dano": lambda i: dnd.dano_request(self.sheet, item(i).get("dano"),
                                                    f"{item(i).get('nome') or 'Ataque'} (dano)")}
        self._list_rows(scroll, path, self.sheet["ataques"], self.ATTACK_COLS, keys,
                        lambda i: self._remove(path, i, self._populate_attacks), wrap_key="descricao",
                        placeholder="Alcance, propriedades, efeito ao acertar...", rolls=rolls,
                        affixes={"ataque": ("Ataque", None), "dano": ("Dano", None)})
        ctk.CTkLabel(view, text="Ataque: número (+5) ou atributo (FOR, DES +1 = atributo + proficiência + 1). "
                                "Dano: 1d8+FOR usa o modificador. Shift = vantagem, Ctrl = desvantagem.",
                     font=ctk.CTkFont(size=9, slant="italic"), text_color=TEXT_FAINT, wraplength=560,
                     justify=tk.LEFT).pack(anchor=tk.W, pady=(4, 0))

    # Magias (p. 201-205)
    SPELL_COLS = [(160, True), (56, False), (260, True)]

    def _build_spells(self, view):
        top = ctk.CTkFrame(view, fg_color=PANEL_DARK, corner_radius=6)
        top.pack(fill=tk.X, pady=(0, 8))
        line = ctk.CTkFrame(top, fg_color="transparent")
        line.pack(fill=tk.X, padx=8, pady=(8, 4))
        self._caption(line, "CLASSE").pack(side=tk.LEFT)
        self._field(line, ("magias", "classe_conjurador"), width=110, placeholder="Mago").pack(side=tk.LEFT, padx=6)
        self._caption(line, "ATRIBUTO").pack(side=tk.LEFT, padx=(8, 0))
        self._option(line, ("magias", "atributo"), [NO_ATTR] + list(SIGLAS.values()), width=70, kind="atributo",
                     parse=lambda label: next((a for a, s in SIGLAS.items() if s == label), "")).pack(
            side=tk.LEFT, padx=6)
        for caption, key, fn in (("CD", "cd_salvamento", dnd.cd_magia), ("ATAQUE", "bonus_ataque", dnd.ataque_magia)):
            self._caption(line, caption).pack(side=tk.LEFT, padx=(10, 4))
            if self._built_manual_spells:  # sem atributo de conjuração: digitado à mão
                self._field(line, ("magias", key), kind="int", width=40, justify="center").pack(side=tk.LEFT)
                if key == "bonus_ataque":
                    self._roll_button(line, lambda: dnd.ataque_magia_request(self.sheet)).pack(side=tk.LEFT, padx=2)
            elif key == "cd_salvamento":
                self._value_label(line, lambda: dnd.cd_magia(self.sheet), size=14).pack(side=tk.LEFT)
            else:
                self._bonus_button(line, lambda: dnd.ataque_magia_request(self.sheet),
                                   lambda: fmt_bonus(dnd.ataque_magia(self.sheet))).pack(side=tk.LEFT)
        hint = ctk.CTkLabel(top, text="", font=ctk.CTkFont(size=9, slant="italic"), text_color=TEXT_FAINT)
        hint.pack(anchor=tk.W, padx=8)
        self._computed(lambda: update(hint, text=(
            "Sem atributo de conjuração: CD e ataque são digitados. Escolha o atributo (ou escreva a classe) "
            "para calcular." if dnd.atributo_conjuracao(self.sheet) is None else
            "CD = 8 + modificador + proficiência; ataque = modificador + proficiência (p. 205).")))

        slots = ctk.CTkFrame(top, fg_color="transparent")
        slots.pack(fill=tk.X, padx=6, pady=(2, 8))
        for lvl in range(1, 10):
            slots.grid_columnconfigure(lvl - 1, weight=1)
            cell = ctk.CTkFrame(slots, fg_color=PANEL, corner_radius=5)
            cell.grid(row=0, column=lvl - 1, padx=1, sticky="nsew")
            self._caption(cell, f"{lvl}º").pack()
            vals = ctk.CTkFrame(cell, fg_color="transparent")
            vals.pack(pady=(0, 3))
            path = ("magias", "slots", str(lvl))
            self._field(vals, path + ("atual",), kind="int", width=22, height=18, size=10, justify="center",
                        clamp=lambda v, p=path: max(0, min(v, self._get(p)["max"]))).pack(side=tk.LEFT)
            ctk.CTkLabel(vals, text="/", font=ctk.CTkFont(size=9), text_color=TEXT_MUTED, width=6).pack(side=tk.LEFT)
            self._field(vals, path + ("max",), kind="int", width=22, height=18, size=10, justify="center",
                        clamp=lambda v: max(0, v)).pack(side=tk.LEFT)

        self.spell_list_view = ctk.CTkFrame(view, fg_color="transparent")
        self.spell_list_view.pack(fill=tk.BOTH, expand=True)
        self._populate_spell_list()

    def _populate_spell_list(self):
        """Magias em ordem de nível (truques primeiro). Mudar o nível reordena a lista."""
        view = self.spell_list_view
        for child in view.winfo_children():
            child.destroy()
        path = ("magias", "lista")

        def add(entries):
            nome, nivel, descricao = (e.get().strip() for e in entries)
            nivel = 0 if nivel.lower().startswith("t") else max(0, min(to_int(nivel, 0), 9))
            self._append(path, {"nome": nome, "nivel": nivel, "descricao": descricao}, entries,
                         self._populate_spell_list)

        scroll = self._list_section(view, self.SPELL_COLS, ("Magia ou truque", "Nível", "Tempo, alcance, efeito..."),
                                    add)
        lista = self.sheet["magias"]["lista"]
        for idx in sorted(range(len(lista)), key=lambda i: (lista[i]["nivel"], lista[i]["nome"].lower())):
            base = path + (idx,)
            row = ctk.CTkFrame(scroll, fg_color=PANEL)
            row.pack(fill=tk.X, pady=3, padx=4)
            line = ctk.CTkFrame(row, fg_color="transparent")
            line.pack(fill=tk.X)
            small_button(line, "X", lambda i=idx: self._remove(path, i, self._populate_spell_list), width=24,
                         danger=True, height=20).pack(side=tk.RIGHT, padx=8)
            menu = self._option(line, base + ("nivel",), NIVEIS_MAGIA, width=78, kind="nivel_magia",
                                parse=NIVEIS_MAGIA.index)
            menu.configure(command=lambda label, b=base: (self._commit(b + ("nivel",), NIVEIS_MAGIA.index(label)),
                                                          self.after_idle(self._populate_spell_list)))
            menu.pack(side=tk.LEFT, padx=(6, 3), pady=3)
            self._field(line, base + ("nome",), width=120, transparent=True, bold=True, size=12,
                        text_color=self.color).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
            self._textbox(row, base + ("descricao",), auto_height=True, text_color=TEXT_DIM,
                          placeholder="Tempo de conjuração, alcance, componentes, duração, efeito...").pack(
                fill=tk.X, padx=6, pady=(0, 6))

    # Características, idiomas e proficiências
    FEATURE_COLS = [(160, True), (300, True)]

    def _build_features(self, view):
        top = ctk.CTkFrame(view, fg_color="transparent")
        top.pack(fill=tk.X, pady=(0, 8))
        top.grid_columnconfigure(1, weight=1)
        for r, (label, key, hint) in enumerate((("IDIOMAS", "idiomas", "ex.: Comum, Élfico"),
                                                ("PROFICIÊNCIAS", "proficiencias",
                                                 "ex.: armaduras leves, espadas curtas, kit de ladrão"))):
            self._caption(top, label).grid(row=r, column=0, sticky="nw", pady=(6, 2), padx=(0, 8))
            self._textbox(top, (key,), framed=True, placeholder=hint).grid(row=r, column=1, sticky="ew", pady=2)
        self.features_view = ctk.CTkFrame(view, fg_color="transparent")
        self.features_view.pack(fill=tk.BOTH, expand=True)
        self._populate_features()

    def _populate_features(self):
        view = self.features_view
        for child in view.winfo_children():
            child.destroy()
        keys, path = ("nome", "detalhes"), ("caracteristicas",)
        scroll = self._list_section(
            view, self.FEATURE_COLS, ("Característica ou talento", "Descrição"),
            lambda es: self._append(path, {k: e.get().strip() for k, e in zip(keys, es)}, es,
                                    self._populate_features))
        self._list_rows(scroll, path, self.sheet["caracteristicas"], self.FEATURE_COLS, keys,
                        lambda i: self._remove(path, i, self._populate_features), wrap_key="detalhes",
                        placeholder="O que a característica faz...")

    # Inventário (lista de textos)
    def _populate_inventory(self):
        view = self.inventory_view
        for child in view.winfo_children():
            child.destroy()
        path = ("inventario",)

        def add(entries):
            text = entries[0].get().strip()
            if text:
                self.sheet["inventario"].append(text)
                entries[0].delete(0, tk.END)
                self._populate_inventory()
                self._changed()

        scroll = self._list_section(view, [(300, True)], ("Item (ex.: Corda de cânhamo, 15 m)",), add)
        for idx in range(len(self.sheet["inventario"])):
            row = ctk.CTkFrame(scroll, fg_color=PANEL)
            row.pack(fill=tk.X, pady=2, padx=4)
            small_button(row, "X", lambda i=idx: self._remove(path, i, self._populate_inventory), width=24,
                         danger=True, height=20).pack(side=tk.RIGHT, padx=8)
            self._field(row, path + (idx,), width=200, transparent=True).pack(side=tk.LEFT, fill=tk.X, expand=True,
                                                                             padx=6, pady=3)

    # Extra (recursos e listas próprias de cada ficha)
    def _build_extra(self, view):
        self.extra_views = {}
        extra = self.sheet.get("extra", {})
        if not extra:
            ctk.CTkLabel(view, text="Esta ficha não tem recursos extras.", text_color=TEXT_FAINT).pack(pady=20)
            return
        scroll = ctk.CTkScrollableFrame(view, fg_color=PANEL_DARK)
        scroll.pack(fill=tk.BOTH, expand=True)
        for key in extra:
            self._caption(scroll, EXTRA_NAMES.get(key, key.replace("_", " ")).upper()).pack(
                anchor=tk.W, padx=8, pady=(8, 2))
            self.extra_views[key] = ctk.CTkFrame(scroll, fg_color="transparent")
            self.extra_views[key].pack(fill=tk.X)
            self._populate_extra(key)

    def _extra_path(self, key):
        category = self.sheet["extra"].get(key)
        return ("extra", key, "lista") if isinstance(category, dict) else ("extra", key)

    def _populate_extra(self, key):
        view = self.extra_views.get(key)
        if view is None:
            return
        for child in view.winfo_children():
            child.destroy()
        category = self.sheet["extra"].get(key)
        path = self._extra_path(key)
        items = self._get(path) or []
        maximo = category.get("maximo") if isinstance(category, dict) else None
        if maximo is not None:
            line = ctk.CTkFrame(view, fg_color="transparent")
            line.pack(fill=tk.X, padx=6, pady=(0, 4))
            ctk.CTkLabel(line, text=f"{len(items)} / {maximo}", font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=TEXT_DIM).pack(side=tk.LEFT, padx=(2, 8))
            if len(items) < maximo:
                name = ctk.CTkEntry(line, height=24, placeholder_text="Nome", font=ctk.CTkFont(size=11))
                name.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
                effect = ctk.CTkEntry(line, height=24, placeholder_text="Efeito", font=ctk.CTkFont(size=11))
                effect.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
                add = small_button(line, "Adicionar", lambda: self._add_extra(key, name, effect), width=70, height=24)
                add.pack(side=tk.LEFT, padx=2)
                for entry in (name, effect):
                    entry.bind("<Return>", lambda *_: add.invoke())
        for idx, item in enumerate(items):
            row = ctk.CTkFrame(view, fg_color=PANEL)
            row.pack(fill=tk.X, pady=2, padx=4)
            if not isinstance(item, dict):
                self._field(row, path + (idx,), width=200, transparent=True).pack(fill=tk.X, padx=6, pady=3)
                continue
            line = ctk.CTkFrame(row, fg_color="transparent")
            line.pack(fill=tk.X)
            small_button(line, "X", lambda i=idx: self._remove(path, i, lambda: self._populate_extra(key)), width=24,
                         danger=True, height=20).pack(side=tk.RIGHT, padx=8)
            if "valor_atual" in item:
                self._field(line, path + (idx, "valor_maximo"), width=32, transparent=True,
                            justify="center").pack(side=tk.RIGHT)
                ctk.CTkLabel(line, text="/", text_color=TEXT_MUTED).pack(side=tk.RIGHT)
                self._field(line, path + (idx, "valor_atual"), width=32, justify="center").pack(side=tk.RIGHT)
            self._field(line, path + (idx, "nome"), width=160, transparent=True, bold=True, size=12,
                        text_color=self.color).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3, pady=3)
            detail_key = "efeito" if "efeito" in item else "detalhes"
            self._textbox(row, path + (idx, detail_key), auto_height=True, text_color=TEXT_DIM,
                          placeholder="Detalhes...").pack(fill=tk.X, padx=6, pady=(0, 6))

    def _add_extra(self, key, name_entry, effect_entry):
        name = name_entry.get().strip()
        category = self.sheet["extra"].get(key)
        items = self._get(self._extra_path(key))
        if name and (not isinstance(category, dict) or len(items) < category.get("maximo", 3)):
            items.append({"nome": name, "efeito": effect_entry.get().strip()})
            self._populate_extra(key)
            self._changed()

