"""Janela do mestre: servidor + lista de jogadores + ficha selecionada.

Uso: uv run dm.py [--port 5000]
"""
import argparse
import json
import os
import socket
import tkinter as tk
from dataclasses import dataclass
from tkinter import filedialog, messagebox

import customtkinter as ctk

from src import ordem
from src.net.protocol import DEFAULT_PORT
from src.net.server import DM_NAME, DNDServer
from src.ui.dice_window import DiceWindow
from src.ui.initiative_window import InitiativeWindow
from src.sheet_io import SYSTEMS, create_new_sheet, create_new_threat, load_sheet, save_sheet
from src.ui.common import (BG, BORDER, BUTTON, BUTTON_HOVER, ERROR, OK, PANEL, PANEL_DARK, TEXT_DIM, TEXT_FAINT,
                           TEXT_MUTED, TITLE_FONT, WARN, UiDispatcher, allow_ctrl_c, bring_to_front,
                           install_click_defocus, update, update_bar)
from src.ui.systems import iniciativa_request, make_sheet_view, resources

PREFS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".dm-prefs.json")


@dataclass
class Entry:
    """Um item da barra lateral: jogador da rede ou ficha aberta localmente."""
    key: str
    label: str
    is_player: bool
    filepath: str | None = None
    sheet: dict | None = None
    online: bool = False


def local_ip() -> str:
    """IP desta máquina na rede local (o que os jogadores digitam). Não envia nenhum pacote."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def load_prefs() -> dict:
    try:
        with open(PREFS_PATH, encoding="utf-8") as file:
            return json.load(file)
    except (OSError, ValueError):
        return {}


def save_prefs(prefs: dict):
    try:
        with open(PREFS_PATH, "w", encoding="utf-8") as file:
            json.dump(prefs, file)
    except OSError:
        pass


class DMApp:
    def __init__(self, port=DEFAULT_PORT, system=None):
        ctk.set_appearance_mode("dark")
        self.root = ctk.CTk()
        self.root.title("Fichas - Mestre")
        self.root.configure(fg_color=BG)
        self.closed = False
        self.server = None
        self._ctrl_c = allow_ctrl_c(self.root, self.on_close)
        bring_to_front(self.root)

        self.entries: dict[str, Entry] = {}
        self.selected: str | None = None
        self.view = None

        # O mestre define o sistema da sessão; todas as fichas seguem ele.
        self.system = system if system in SYSTEMS else self._pick_system()
        if self.system is None:
            self.closed = True
            self.root.destroy()
            return
        save_prefs({**load_prefs(), "system": self.system})
        self.system_label = SYSTEMS[self.system][0]
        self.root.title(f"Fichas - Mestre ({self.system_label})")
        self.root.geometry("1350x780")
        self.root.minsize(1200, 700)

        self.server = DNDServer(port=port, system=self.system)
        ui = UiDispatcher(self.root)
        self.server.on_connect = ui.wrap(self.on_player_connect)
        self.server.on_disconnect = ui.wrap(self.on_player_disconnect)
        self.server.on_update = ui.wrap(self.on_player_update)
        self.server.on_error = ui.wrap(self.on_server_error)
        self.server.on_roll = ui.wrap(self.on_roll)
        self.rolls = []
        self.dice_window = None
        self.initiative = None
        self.views = {}              # tela já montada de cada ficha (trocar de ficha não remonta)
        self._sidebar_layout = None  # forma dos cartões da barra lateral na última vez
        self._card_values = {}       # rótulo e barra de cada recurso, para atualizar no lugar
        self._cards = {}             # cartão de cada ficha na barra lateral

        self._build_ui()
        install_click_defocus(self.root)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        try:
            self.server.start()
            self.lbl_address.configure(text=f"Endereço para os jogadores:\n{local_ip()}:{self.server.port}")
        except OSError as exc:
            messagebox.showerror("Erro de servidor",
                                 f"Não foi possível abrir o servidor na porta {port}:\n{exc}\n\n"
                                 "Você ainda pode abrir fichas locais.")
            self.lbl_address.configure(text="Servidor desligado", text_color=ERROR)

    # ================================================================= interface
    def _pick_system(self):
        """Tela inicial: o mestre escolhe o sistema da sessão. Devolve a chave ou None (janela fechada)."""
        self.root.geometry("460x300")
        self.root.resizable(False, False)
        choice = tk.StringVar(value="")
        last = load_prefs().get("system")

        frame = ctk.CTkFrame(self.root, fg_color=BG, corner_radius=0)
        frame.pack(fill=tk.BOTH, expand=True)
        ctk.CTkLabel(frame, text="NOVA SESSÃO", font=ctk.CTkFont(family=TITLE_FONT, size=20, weight="bold"),
                     text_color="#ffffff").pack(pady=(34, 6))
        ctk.CTkLabel(frame, text="Qual sistema vai ser usado nesta sessão?", text_color=TEXT_DIM).pack(pady=(0, 18))
        for key, (label, _) in SYSTEMS.items():
            ctk.CTkButton(frame, text=label, width=300, height=40, font=ctk.CTkFont(size=14, weight="bold"),
                          fg_color=BUTTON_HOVER if key == last else BUTTON, hover_color="#4a4a4a",
                          border_width=1 if key == last else 0, border_color=TEXT_MUTED,
                          command=lambda k=key: choice.set(k)).pack(pady=6)

        self.root.protocol("WM_DELETE_WINDOW", lambda: choice.set("__closed__"))
        self._ctrl_c["handler"] = lambda: choice.set("__closed__")
        # O CTk nasce escondido e só aparece no mainloop(); aqui ainda não chegamos nele.
        self.root.deiconify()
        self.root.wait_variable(choice)
        self._ctrl_c["handler"] = self.on_close
        frame.destroy()
        self.root.resizable(True, True)
        return None if choice.get() == "__closed__" else choice.get()

    def _build_ui(self):
        sidebar = ctk.CTkFrame(self.root, width=280, fg_color=PANEL, corner_radius=0)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        sidebar.pack_propagate(False)

        ctk.CTkLabel(sidebar, text=self.system_label.upper(), font=ctk.CTkFont(family=TITLE_FONT, size=14, weight="bold"),
                     text_color="#ffffff").pack(pady=(20, 4))
        self.lbl_address = ctk.CTkLabel(sidebar, text="Iniciando servidor...", font=ctk.CTkFont(size=11),
                                        text_color=TEXT_DIM, justify=tk.CENTER)
        self.lbl_address.pack(pady=(0, 10))

        buttons = ctk.CTkFrame(sidebar, fg_color="transparent")
        buttons.pack(fill=tk.X, padx=10)
        sheet_buttons = [("Abrir ficha", self.open_local_sheet), ("Nova ficha", self.create_sheet)]
        if self.system == ordem.SYSTEM:
            sheet_buttons.append(("Nova ameaça", self.create_threat))
        for text, command in sheet_buttons:
            ctk.CTkButton(buttons, text=text, fg_color=BUTTON, hover_color=BUTTON_HOVER, height=28, width=10,
                          command=command).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
        table = ctk.CTkFrame(sidebar, fg_color="transparent")
        table.pack(fill=tk.X, padx=10, pady=(8, 0))
        for text, command in (("Dados", self.open_dice), ("Iniciativa", self.open_initiative)):
            ctk.CTkButton(table, text=text, fg_color=BUTTON, hover_color=BUTTON_HOVER, height=30, width=10,
                          font=ctk.CTkFont(size=13, weight="bold"), command=command).pack(
                side=tk.LEFT, fill=tk.X, expand=True, padx=3)

        self.list_frame = ctk.CTkScrollableFrame(sidebar, fg_color="transparent")
        self.list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=10)

        self.lbl_status = ctk.CTkLabel(sidebar, text="", font=ctk.CTkFont(size=10), text_color=ERROR,
                                       wraplength=250, justify=tk.LEFT)
        self.lbl_status.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.detail = ctk.CTkFrame(self.root, fg_color="transparent")
        self.detail.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.placeholder = ctk.CTkLabel(self.detail, text="Selecione uma ficha na lista ao lado",
                                        font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXT_FAINT)

        self.refresh_sidebar()
        self.show_selected()

    def refresh_sidebar(self):
        if self.initiative is not None and self.initiative.winfo_exists():
            self.initiative.refresh()
        ordered = self._ordered_entries()
        layout = [self._card_layout(e) for e in ordered]
        if layout and layout == self._sidebar_layout:
            # mesmas fichas, mesma ordem: só os números e as barras mudam (sem refazer e piscar)
            for entry in ordered:
                self._update_card_values(entry)
                update(self._cards[entry.key], **self._card_style(entry))
            return
        self._sidebar_layout = layout
        self._card_values = {}
        self._cards = {}
        for child in self.list_frame.winfo_children():
            child.destroy()
        if not self.entries:
            ctk.CTkLabel(self.list_frame, text="Nenhum jogador conectado.\nAbra uma ficha ou espere os jogadores.",
                         font=ctk.CTkFont(size=11, slant="italic"), text_color=TEXT_FAINT).pack(pady=20)
            return
        for entry in self._ordered_entries():
            self._sidebar_card(entry)

    def _ordered_entries(self):
        """Jogadores, depois fichas locais de agentes, depois ameaças."""
        return sorted(self.entries.values(),
                      key=lambda e: (not e.is_player, ordem.is_ameaca(e.sheet), e.label.lower()))

    def _card_layout(self, entry: Entry):
        """O que muda a forma do cartão (se isso não mudou, só os valores são atualizados)."""
        sheet = entry.sheet
        return (entry.key, entry.label, entry.is_player, entry.online,
                sheet.get("cor") if sheet else None, ordem.is_ameaca(sheet),
                tuple(r[0] for r in resources(sheet)) if sheet else ())

    def _update_card_values(self, entry: Entry):
        if not entry.sheet:
            return
        for (lbl_val, bar, fixed_color), (_sigla, atual, maximo, _c) in zip(self._card_values.get(entry.key, []),
                                                                           resources(entry.sheet)):
            ratio = atual / max(1, maximo)
            update(lbl_val, text=f"{atual}/{maximo}")
            update_bar(bar, ratio)
            if not fixed_color:
                update(bar, progress_color=OK if ratio > 0.3 else ERROR)

    def _card_style(self, entry: Entry):
        """Destaque da ficha selecionada (muda no lugar, sem refazer o cartão)."""
        selected = entry.key == self.selected
        color = entry.sheet.get("cor", "#ffffff") if entry.sheet else "#888888"
        return {"fg_color": "#222222" if selected else PANEL_DARK, "border_width": 2 if selected else 1,
                "border_color": color if selected and entry.sheet else BORDER}

    def _sidebar_card(self, entry: Entry):
        color = entry.sheet.get("cor", "#ffffff") if entry.sheet else "#888888"
        card = ctk.CTkFrame(self.list_frame, corner_radius=8)
        update(card, **self._card_style(entry))
        card.pack(fill=tk.X, pady=5)
        self._cards[entry.key] = card
        widgets = [card]

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill=tk.X, padx=10, pady=(8, 0))
        widgets.append(top)
        if entry.is_player:
            dot = ctk.CTkLabel(top, text="●", font=ctk.CTkFont(size=12), text_color=OK if entry.online else TEXT_FAINT)
            dot.pack(side=tk.LEFT, padx=(0, 6))
            widgets.append(dot)
        name = ctk.CTkLabel(top, text=entry.label.upper(), font=ctk.CTkFont(size=12, weight="bold"),
                            text_color=color if entry.sheet else TEXT_MUTED)
        name.pack(side=tk.LEFT)
        widgets.append(name)
        if not entry.online:
            ctk.CTkButton(top, text="×", width=20, height=18, fg_color="transparent", hover_color="#a83232",
                          text_color=TEXT_MUTED, command=lambda k=entry.key: self.remove_entry(k)).pack(side=tk.RIGHT)

        if entry.sheet:
            for sigla, atual, maximo, res_color in resources(entry.sheet):
                ratio = atual / max(1, maximo)
                row = ctk.CTkFrame(card, fg_color="transparent")
                row.pack(fill=tk.X, padx=10, pady=(4, 0))
                lbl_sigla = ctk.CTkLabel(row, text=sigla, width=30, height=16, anchor="w",
                                         font=ctk.CTkFont(size=10, weight="bold"), text_color=res_color or TEXT_DIM)
                lbl_sigla.pack(side=tk.LEFT)
                lbl_val = ctk.CTkLabel(row, text=f"{atual}/{maximo}", width=48, height=16, anchor="e",
                                       font=ctk.CTkFont(size=10), text_color=TEXT_DIM)
                lbl_val.pack(side=tk.RIGHT)
                bar = ctk.CTkProgressBar(row, fg_color=BUTTON, height=6,
                                         progress_color=res_color or (OK if ratio > 0.3 else ERROR))
                bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
                update_bar(bar, ratio)
                widgets += [row, lbl_sigla, lbl_val, bar]
                self._card_values.setdefault(entry.key, []).append((lbl_val, bar, res_color))
            status = "" if entry.online else ("desconectado" if entry.is_player else
                                              "ameaça" if ordem.is_ameaca(entry.sheet) else "ficha local")
        else:
            status = "Sem ficha (clique para escolher)"
        if status:
            lbl = ctk.CTkLabel(card, text=status, font=ctk.CTkFont(size=10), height=16,
                               text_color=TEXT_FAINT if entry.sheet else WARN)
            lbl.pack(anchor=tk.W, padx=10)
            widgets.append(lbl)
        ctk.CTkFrame(card, fg_color="transparent", height=6).pack()  # respiro embaixo

        for widget in widgets:
            widget.bind("<Button-1>", lambda e, k=entry.key: self.select(k))

    def show_selected(self):
        """Mostra a ficha selecionada. Cada ficha monta a tela uma vez só e fica guardada: trocar de
        ficha é só esconder uma e mostrar a outra (montar de novo é lento e pisca)."""
        entry = self.entries.get(self.selected)
        view = self.views.get(self.selected) if entry and entry.sheet else None
        if entry and entry.sheet and view is None:
            view = make_sheet_view(self.detail, entry.sheet, on_change=lambda s, k=entry.key: self.on_dm_edit(k, s),
                                   on_roll=lambda req, k=entry.key: self.roll_from_sheet(k, req))
            self.views[entry.key] = view
        elif view is not None:
            view.set_sheet(entry.sheet)  # pode ter mudado enquanto estava escondida
        if view is not None:
            view.pack(fill=tk.BOTH, expand=True)  # mostra a nova antes de esconder a antiga
        for other in self.views.values():
            if other is not view:
                other.pack_forget()
        if view is None:
            self.placeholder.pack(expand=True)
        else:
            self.placeholder.pack_forget()
        self.view = view

    def _drop_view(self, key):
        view = self.views.pop(key, None)
        if view is not None:
            view.destroy()
        if self.view is view:
            self.view = None

    # ================================================================= ações do mestre
    def select(self, key):
        entry = self.entries.get(key)
        if not entry:
            return
        if entry.is_player and not entry.sheet:
            if not self.assign_sheet_to(entry):
                return
        self.selected = key
        self.refresh_sidebar()
        self.show_selected()

    def assign_sheet_to(self, entry: Entry) -> bool:
        path = filedialog.askopenfilename(title=f"Escolher ficha para {entry.label}",
                                          filetypes=[("Fichas JSON", "*.json")], initialdir=self._sheets_dir())
        if not path:
            return False
        sheet = self._load(path)
        if sheet is None:
            return False
        if ordem.is_ameaca(sheet):
            messagebox.showerror("Ficha de ameaça", f"{os.path.basename(path)} é uma ficha de ameaça. "
                                                    "Ameaças são só do mestre: abra com Abrir ficha.")
            return False
        entry.filepath, entry.sheet = path, sheet
        self._drop_view(entry.key)
        self.server.assign_sheet(entry.label, path, sheet)
        return True

    def open_local_sheet(self):
        """Abre uma ou várias fichas (Ctrl/Shift no explorador). Erros aparecem juntos num aviso só."""
        paths = filedialog.askopenfilenames(title="Abrir fichas", filetypes=[("Fichas JSON", "*.json")],
                                            initialdir=self._sheets_dir())
        if not paths:
            return
        opened, errors = [], []
        for path in paths:
            sheet, error = self._read_sheet(path)
            if error:
                errors.append(error)
            else:
                opened.append(self._register_local(path, sheet))
        if opened:
            self.selected = opened[0]
            self.refresh_sidebar()
            self.show_selected()
        if errors:
            title = "Ficha não aberta" if len(errors) == 1 else f"{len(errors)} fichas não abertas"
            messagebox.showerror(title, "\n\n".join(errors))

    def create_sheet(self):
        dialog = ctk.CTkInputDialog(title="Nova ficha", text=f"Nome do personagem ({self.system_label}):")
        name = (dialog.get_input() or "").strip()
        if not name:
            return
        path = filedialog.asksaveasfilename(title="Salvar ficha nova", defaultextension=".json",
                                            initialdir=self._sheets_dir(), initialfile=f"{name}.json",
                                            filetypes=[("Fichas JSON", "*.json")])
        if not path:
            return
        try:
            create_new_sheet(name, self.system, path)
        except OSError as exc:
            messagebox.showerror("Erro", f"Não foi possível criar a ficha:\n{exc}")
            return
        self._add_local(path)

    def create_threat(self):
        dialog = ctk.CTkInputDialog(title="Nova ameaça", text="Nome da ameaça:")
        name = (dialog.get_input() or "").strip()
        if not name:
            return
        npcs = os.path.join(self._sheets_dir(), "npcs")
        path = filedialog.asksaveasfilename(title="Salvar ameaça nova", defaultextension=".json",
                                            initialdir=npcs if os.path.isdir(npcs) else self._sheets_dir(),
                                            initialfile=f"{name}.json", filetypes=[("Fichas JSON", "*.json")])
        if not path:
            return
        try:
            create_new_threat(name, path)
        except OSError as exc:
            messagebox.showerror("Erro", f"Não foi possível criar a ameaça:\n{exc}")
            return
        self._add_local(path)

    def _add_local(self, path):
        sheet = self._load(path)
        if sheet is None:
            return
        self.selected = self._register_local(path, sheet)
        self.refresh_sidebar()
        self.show_selected()

    def _register_local(self, path, sheet) -> str:
        """Coloca a ficha na lista (sem redesenhar). Abrir o mesmo arquivo de novo só atualiza."""
        key = "local:" + os.path.normcase(os.path.abspath(path))
        self._drop_view(key)  # abriu de novo: monta com o que está no arquivo
        self.entries[key] = Entry(key=key, label=sheet.get("nome", os.path.basename(path)), is_player=False,
                                  filepath=path, sheet=sheet)
        return key

    def remove_entry(self, key):
        entry = self.entries.pop(key, None)
        self._drop_view(key)
        if entry and entry.is_player:
            self.server.forget(entry.label)
        if self.selected == key:
            self.selected = None
            self.show_selected()
        self.refresh_sidebar()

    def on_dm_edit(self, key, sheet):
        entry = self.entries.get(key)
        if not entry:
            return
        entry.sheet = sheet
        if entry.is_player:
            self.server.update_from_dm(entry.label, sheet)
        else:
            try:
                save_sheet(sheet, entry.filepath)
            except OSError as exc:
                self.on_server_error(None, f"Falha ao salvar {entry.filepath}: {exc}")
        self.refresh_sidebar()

    # ================================================================= dados
    def open_dice(self):
        if self.dice_window is None or not self.dice_window.winfo_exists():
            self.dice_window = DiceWindow(
                self.root, DM_NAME, allow_private=True,
                on_roll=lambda req: bool(self.server.roll_as_dm(req, private=req.get("private", False))))
            self.dice_window.set_history(self.rolls)
        self.dice_window.show()

    def roll_from_sheet(self, key, req):
        """Botão de rolar numa ficha: abre a janela de dados (se precisar) e rola com o nome da ficha."""
        entry = self.entries.get(key)
        name = entry.sheet.get("nome", entry.label) if entry and entry.sheet else ""
        self.open_dice()
        self.dice_window.roll_request({**req, "label": f"{name} · {req.get('label', '')}".strip(" ·")})

    # ================================================================= iniciativa
    def open_initiative(self):
        if self.initiative is None or not self.initiative.winfo_exists():
            self.initiative = InitiativeWindow(
                self.root, get_entries=self._initiative_entries, roll=self._initiative_roll,
                request_for=iniciativa_request, on_select=self.select, resources=resources)
        self.initiative.show()

    def _initiative_entries(self):
        return [(e.key, e.sheet.get("nome", e.label), e.sheet, ordem.is_ameaca(e.sheet))
                for e in self._ordered_entries() if e.sheet]

    def _initiative_roll(self, req, private):
        try:
            return self.server.roll_as_dm(req, private=private)
        except (TypeError, ValueError):
            return None

    def on_roll(self, result):
        self.rolls = (self.rolls + [result])[-50:]
        if self.dice_window is not None and self.dice_window.winfo_exists():
            self.dice_window.add_roll(result)

    # ================================================================= eventos da rede
    def on_player_connect(self, name, addr):
        entry = self.entries.get(name)
        if entry is None:
            entry = Entry(key=name, label=name, is_player=True)
            self.entries[name] = entry
        entry.online = True
        if entry.sheet is None:
            entry.sheet = self.server.get_sheet(name)
        self.refresh_sidebar()

    def on_player_disconnect(self, name):
        entry = self.entries.get(name)
        if not entry:
            return
        if entry.sheet is None:
            # Nunca recebeu ficha: some da lista
            del self.entries[name]
            if self.selected == name:
                self.selected = None
                self.show_selected()
        else:
            # Mantém na lista como desconectado; volta sozinho com a mesma ficha
            entry.online = False
        self.refresh_sidebar()

    def on_player_update(self, name, sheet):
        entry = self.entries.get(name)
        if not entry:
            return
        entry.sheet = sheet
        if self.selected == name and self.view is not None:
            self.view.set_sheet(sheet)
        self.refresh_sidebar()

    def on_server_error(self, name, msg):
        self.lbl_status.configure(text=f"{name + ': ' if name else ''}{msg}")
        self.root.after(8000, lambda: self.lbl_status.configure(text=""))

    # ================================================================= utilidades
    def _read_sheet(self, path):
        """(ficha, None) ou (None, mensagem de erro). Confere se é do sistema da sessão."""
        name = os.path.basename(path)
        try:
            sheet = load_sheet(path)
        except (OSError, ValueError) as exc:
            return None, f"Não foi possível ler {name}:\n{exc}"
        system = sheet.get("sistema")
        if system != self.system:
            other = SYSTEMS.get(system, (system or "desconhecido",))[0]
            return None, f"{name} é uma ficha de {other}, mas esta sessão é de {self.system_label}."
        return sheet, None

    def _load(self, path):
        """Carrega uma ficha; se der erro, mostra o aviso e devolve None."""
        sheet, error = self._read_sheet(path)
        if error:
            messagebox.showerror("Erro ao abrir ficha", error)
        return sheet

    @staticmethod
    def _sheets_dir():
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "sheets")

    def on_close(self):
        if self.server:
            self.server.stop()
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def run(self):
        if not self.closed:
            self.root.mainloop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Janela do mestre")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--sistema", choices=list(SYSTEMS),
                        help="sistema da sessão (sem isso, o app pergunta ao abrir)")
    args = parser.parse_args()
    DMApp(port=args.port, system=args.sistema).run()
