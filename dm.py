"""Janela do mestre: servidor + lista de jogadores + ficha selecionada.

Uso: uv run dm.py [--port 5000]
"""
import argparse
import os
import socket
import tkinter as tk
from dataclasses import dataclass
from tkinter import filedialog, messagebox

import customtkinter as ctk

from src.net.protocol import DEFAULT_PORT
from src.net.server import DNDServer
from src.sheet_io import SYSTEMS, create_new_sheet, load_sheet, save_sheet
from src.ui.common import (BG, BORDER, BUTTON, BUTTON_HOVER, ERROR, OK, PANEL, PANEL_DARK, TEXT_DIM, TEXT_FAINT,
                           TEXT_MUTED, TITLE_FONT, WARN, UiDispatcher, install_click_defocus)
from src.ui.systems import life, make_sheet_view


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


class DMApp:
    def __init__(self, port=DEFAULT_PORT):
        ctk.set_appearance_mode("dark")
        self.root = ctk.CTk()
        self.root.title("Fichas - Mestre")
        self.root.geometry("1350x780")
        self.root.minsize(1200, 700)
        self.root.configure(fg_color=BG)

        self.entries: dict[str, Entry] = {}
        self.selected: str | None = None
        self.view = None

        self.server = DNDServer(port=port)
        ui = UiDispatcher(self.root)
        self.server.on_connect = ui.wrap(self.on_player_connect)
        self.server.on_disconnect = ui.wrap(self.on_player_disconnect)
        self.server.on_update = ui.wrap(self.on_player_update)
        self.server.on_error = ui.wrap(self.on_server_error)

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
    def _build_ui(self):
        sidebar = ctk.CTkFrame(self.root, width=280, fg_color=PANEL, corner_radius=0)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        sidebar.pack_propagate(False)

        ctk.CTkLabel(sidebar, text="FICHAS", font=ctk.CTkFont(family=TITLE_FONT, size=13, weight="bold"),
                     text_color=TEXT_MUTED).pack(pady=(20, 4))
        self.lbl_address = ctk.CTkLabel(sidebar, text="Iniciando servidor...", font=ctk.CTkFont(size=11),
                                        text_color=TEXT_DIM, justify=tk.CENTER)
        self.lbl_address.pack(pady=(0, 10))

        buttons = ctk.CTkFrame(sidebar, fg_color="transparent")
        buttons.pack(fill=tk.X, padx=10)
        for text, command in (("Abrir ficha", self.open_local_sheet), ("Nova ficha", self.create_sheet)):
            ctk.CTkButton(buttons, text=text, fg_color=BUTTON, hover_color=BUTTON_HOVER, height=28,
                          command=command).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)

        self.list_frame = ctk.CTkScrollableFrame(sidebar, fg_color="transparent")
        self.list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=10)

        self.lbl_status = ctk.CTkLabel(sidebar, text="", font=ctk.CTkFont(size=10), text_color=ERROR,
                                       wraplength=250, justify=tk.LEFT)
        self.lbl_status.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.detail = ctk.CTkFrame(self.root, fg_color="transparent")
        self.detail.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.refresh_sidebar()
        self.show_selected()

    def refresh_sidebar(self):
        for child in self.list_frame.winfo_children():
            child.destroy()
        if not self.entries:
            ctk.CTkLabel(self.list_frame, text="Nenhum jogador conectado.\nAbra uma ficha ou espere os jogadores.",
                         font=ctk.CTkFont(size=11, slant="italic"), text_color=TEXT_FAINT).pack(pady=20)
            return
        players = sorted((e for e in self.entries.values() if e.is_player), key=lambda e: e.label.lower())
        local = sorted((e for e in self.entries.values() if not e.is_player), key=lambda e: e.label.lower())
        for entry in players + local:
            self._sidebar_card(entry)

    def _sidebar_card(self, entry: Entry):
        selected = entry.key == self.selected
        color = entry.sheet.get("cor", "#ffffff") if entry.sheet else "#888888"
        card = ctk.CTkFrame(self.list_frame, fg_color="#222222" if selected else PANEL_DARK, corner_radius=8,
                            border_width=2 if selected else 1, border_color=color if selected and entry.sheet else BORDER,
                            height=74)
        card.pack(fill=tk.X, pady=5)
        card.pack_propagate(False)
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
            label, hp, hp_max = life(entry.sheet)
            ratio = hp / max(1, hp_max)
            bar = ctk.CTkProgressBar(card, fg_color=BUTTON, progress_color=OK if ratio > 0.3 else ERROR, height=5)
            bar.pack(fill=tk.X, padx=10, pady=(6, 2))
            bar.set(ratio)
            widgets.append(bar)
            if entry.is_player:
                status = f"{label}: {hp} / {hp_max}" + ("" if entry.online else "  ·  desconectado")
            else:
                status = f"{label}: {hp} / {hp_max}  ·  ficha local"
        else:
            status = "Sem ficha (clique para escolher)"
        lbl = ctk.CTkLabel(card, text=status, font=ctk.CTkFont(size=10), text_color=TEXT_DIM if entry.sheet else WARN)
        lbl.pack(anchor=tk.W, padx=10, pady=(1, 4))
        widgets.append(lbl)

        for widget in widgets:
            widget.bind("<Button-1>", lambda e, k=entry.key: self.select(k))

    def show_selected(self):
        for child in self.detail.winfo_children():
            child.destroy()
        self.view = None
        entry = self.entries.get(self.selected)
        if not entry or not entry.sheet:
            ctk.CTkLabel(self.detail, text="Selecione uma ficha na lista ao lado", font=ctk.CTkFont(size=16, weight="bold"),
                         text_color=TEXT_FAINT).pack(expand=True)
            return
        self.view = make_sheet_view(self.detail, entry.sheet, on_change=lambda s, k=entry.key: self.on_dm_edit(k, s))
        self.view.pack(fill=tk.BOTH, expand=True)

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
        entry.filepath, entry.sheet = path, sheet
        self.server.assign_sheet(entry.label, path, sheet)
        return True

    def open_local_sheet(self):
        path = filedialog.askopenfilename(title="Abrir ficha", filetypes=[("Fichas JSON", "*.json")],
                                          initialdir=self._sheets_dir())
        if path:
            self._add_local(path)

    def create_sheet(self):
        choice = self._ask_new_sheet()
        if not choice:
            return
        name, system = choice
        path = filedialog.asksaveasfilename(title="Salvar ficha nova", defaultextension=".json",
                                            initialdir=self._sheets_dir(), initialfile=f"{name}.json",
                                            filetypes=[("Fichas JSON", "*.json")])
        if not path:
            return
        try:
            create_new_sheet(name, system, path)
        except OSError as exc:
            messagebox.showerror("Erro", f"Não foi possível criar a ficha:\n{exc}")
            return
        self._add_local(path)

    def _ask_new_sheet(self):
        """Janela com nome + sistema. Devolve (nome, chave_do_sistema) ou None."""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Nova ficha")
        dialog.geometry("360x220")
        dialog.resizable(False, False)
        dialog.configure(fg_color=BG)
        dialog.transient(self.root)
        result = {}

        ctk.CTkLabel(dialog, text="Nome do personagem", text_color=TEXT_DIM).pack(pady=(18, 4))
        name = ctk.CTkEntry(dialog, width=280, fg_color=PANEL, border_color=BORDER)
        name.pack()
        ctk.CTkLabel(dialog, text="Sistema", text_color=TEXT_DIM).pack(pady=(12, 4))
        labels = {label: key for key, (label, _) in SYSTEMS.items()}
        system = ctk.CTkSegmentedButton(dialog, values=list(labels))
        system.set(next(iter(labels)))
        system.pack()

        def confirm(_event=None):
            if name.get().strip():
                result["value"] = (name.get().strip(), labels[system.get()])
                dialog.destroy()

        ctk.CTkButton(dialog, text="Criar", fg_color=BUTTON, hover_color=BUTTON_HOVER, width=280,
                      command=confirm).pack(pady=16)
        name.bind("<Return>", confirm)
        dialog.after(100, lambda: (dialog.grab_set(), name.focus_set()))
        self.root.wait_window(dialog)
        return result.get("value")

    def _add_local(self, path):
        sheet = self._load(path)
        if sheet is None:
            return
        key = "local:" + os.path.normcase(os.path.abspath(path))
        self.entries[key] = Entry(key=key, label=sheet.get("nome", os.path.basename(path)), is_player=False,
                                  filepath=path, sheet=sheet)
        self.selected = key
        self.refresh_sidebar()
        self.show_selected()

    def remove_entry(self, key):
        entry = self.entries.pop(key, None)
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
    def _load(self, path):
        try:
            return load_sheet(path)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Erro ao abrir ficha", f"Não foi possível ler {os.path.basename(path)}:\n{exc}")
            return None

    @staticmethod
    def _sheets_dir():
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "sheets")

    def on_close(self):
        self.server.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Janela do mestre")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    DMApp(port=parser.parse_args().port).run()
