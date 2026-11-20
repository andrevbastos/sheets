"""Servidor do mestre: aceita jogadores, envia fichas e recebe atualizações."""
import copy
import socket
import threading
from dataclasses import dataclass, field

from src.net.protocol import (DEFAULT_PORT, HEARTBEAT_INTERVAL, HEARTBEAT_TIMEOUT,
                              PROTOCOL_VERSION, Connection, ConnectionClosed)
from src import dice
from src.sheet_io import normalize_sheet, save_sheet

DM_NAME = "Mestre"
HISTORY_SIZE = 50


@dataclass
class Assignment:
    """Ficha vinculada a um personagem. Sobrevive a desconexões durante a sessão."""
    filepath: str
    sheet: dict
    file_lock: threading.Lock = field(default_factory=threading.Lock)


class DNDServer:
    """Callbacks (chamados em threads de rede; a GUI deve repassar com root.after):
        on_connect(name, addr), on_disconnect(name), on_update(name, sheet), on_error(name, msg)
    """

    def __init__(self, host="0.0.0.0", port=DEFAULT_PORT, system=None,
                 heartbeat_interval=HEARTBEAT_INTERVAL, heartbeat_timeout=HEARTBEAT_TIMEOUT):
        self.host = host
        self.port = port
        self.system = system  # sistema da sessão (None = aceita qualquer um)
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout
        self.sock = None
        self.sessions: dict[str, Connection] = {}
        self.assignments: dict[str, Assignment] = {}
        self.rolls = []  # histórico completo (o mestre vê tudo, inclusive as privadas)
        self.lock = threading.RLock()
        self._stopped = threading.Event()

        self.on_connect = None
        self.on_disconnect = None
        self.on_update = None
        self.on_error = None
        self.on_roll = None         # on_roll(resultado completo), para a janela de dados do mestre

    # ------------------------------------------------------------------ ciclo de vida
    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):  # Windows: impede dois servidores na mesma porta
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.port = self.sock.getsockname()[1]  # útil quando port=0 (testes)
        self.sock.listen()
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def stop(self):
        self._stopped.set()
        try:
            self.sock.close()
        except OSError:
            pass
        with self.lock:
            sessions = list(self.sessions.values())
        for conn in sessions:
            conn.close()

    def _accept_loop(self):
        while not self._stopped.is_set():
            try:
                client_sock, addr = self.sock.accept()
            except OSError:
                break
            threading.Thread(target=self._handle_client, args=(client_sock, addr), daemon=True).start()

    # ------------------------------------------------------------------ API para a GUI
    def is_online(self, name: str) -> bool:
        with self.lock:
            conn = self.sessions.get(name)
            return conn is not None and not conn.closed

    def assign_sheet(self, name: str, filepath: str, sheet: dict):
        """Vincula uma ficha ao personagem e envia na hora se ele estiver conectado."""
        sheet = normalize_sheet(sheet)
        if self.system and sheet.get("sistema") != self.system:
            raise ValueError(f"Ficha de {sheet.get('sistema')!r} numa sessão de {self.system!r}")
        with self.lock:
            self.assignments[name] = Assignment(filepath=filepath, sheet=copy.deepcopy(sheet))
            conn = self.sessions.get(name)
        if conn:
            conn.send({"type": "sheet", "sheet": sheet})

    def update_from_dm(self, name: str, sheet: dict):
        """O mestre editou a ficha: salva no disco e envia ao jogador (se conectado)."""
        with self.lock:
            assignment = self.assignments.get(name)
            if not assignment:
                return
            assignment.sheet = copy.deepcopy(sheet)
            conn = self.sessions.get(name)
        self._save(name, assignment, sheet)
        if conn:
            conn.send({"type": "sheet", "sheet": sheet})

    def get_sheet(self, name: str):
        with self.lock:
            assignment = self.assignments.get(name)
            return copy.deepcopy(assignment.sheet) if assignment else None

    def roll(self, request: dict, who: str, private=False) -> dict:
        """Rola um pedido e envia o resultado para todos (privada: os jogadores só sabem que houve)."""
        req = dice.clean_request({**request, "private": private})
        result = dice.roll(req, who)
        with self.lock:
            self.rolls = (self.rolls + [result])[-HISTORY_SIZE:]
            conns = list(self.sessions.values())
        public = dice.hidden(result) if result["private"] else result
        for conn in conns:
            conn.send({"type": "roll", "roll": public})
        self._emit(self.on_roll, result)
        return result

    def roll_as_dm(self, request: dict, private=False) -> dict:
        return self.roll(request, DM_NAME, private=private)

    def _public_history(self):
        with self.lock:
            return [dice.hidden(r) if r["private"] else r for r in self.rolls]

    def forget(self, name: str):
        """Remove o vínculo (o mestre tirou o jogador da lista)."""
        with self.lock:
            self.assignments.pop(name, None)
            conn = self.sessions.pop(name, None)
        if conn:
            conn.send({"type": "kicked", "msg": "O mestre removeu você da sessão."})
            conn.close()

    # ------------------------------------------------------------------ conexão de um jogador
    def _handle_client(self, client_sock, addr):
        conn = Connection(client_sock, self.heartbeat_interval, self.heartbeat_timeout)
        name = None
        try:
            login = conn.recv()
            name = str(login.get("name", "")).strip()
            if login.get("type") != "login" or not name:
                conn.send({"type": "error", "msg": "Login inválido."})
                return
            if name.casefold() == DM_NAME.casefold():
                conn.send({"type": "error", "msg": f'"{DM_NAME}" é reservado. Use o nome do personagem.'})
                return
            if login.get("version") != PROTOCOL_VERSION:
                conn.send({"type": "error", "msg": "Versão do app diferente da do mestre. Atualize os dois."})
                name = None
                return

            # Mesmo nome reconectando (ex.: PC voltou da suspensão): a conexão nova substitui a antiga.
            with self.lock:
                old = self.sessions.get(name)
                self.sessions[name] = conn
                assignment = self.assignments.get(name)
                sheet = copy.deepcopy(assignment.sheet) if assignment else None
            if old:
                old.send({"type": "kicked", "msg": "Outra conexão entrou com este personagem."})
                old.close()

            conn.send({"type": "welcome", "assigned": sheet is not None, "system": self.system,
                       "rolls": self._public_history()})
            if sheet is not None:
                conn.send({"type": "sheet", "sheet": sheet})
            self._emit(self.on_connect, name, addr)

            while True:
                message = conn.recv()
                if message.get("type") == "update":
                    self._apply_player_update(name, message.get("sheet"))
                elif message.get("type") == "roll":
                    try:
                        self.roll(message.get("request") or {}, name)  # jogador nunca rola privado
                    except (TypeError, ValueError):
                        pass
        except ConnectionClosed:
            pass
        except Exception as exc:  # erro inesperado não pode derrubar o servidor
            self._emit(self.on_error, name, str(exc))
        finally:
            conn.close()
            if name:
                with self.lock:
                    is_current = self.sessions.get(name) is conn
                    if is_current:
                        del self.sessions[name]
                if is_current:
                    self._emit(self.on_disconnect, name)

    def _apply_player_update(self, name, sheet):
        if not isinstance(sheet, dict):
            return
        sheet = normalize_sheet(sheet)
        with self.lock:
            assignment = self.assignments.get(name)
            if not assignment:
                return  # ainda sem ficha vinculada: ignora
            if sheet.get("sistema") != assignment.sheet.get("sistema"):
                return  # o jogador não pode trocar o sistema da ficha
            assignment.sheet = copy.deepcopy(sheet)
        self._save(name, assignment, sheet)
        self._emit(self.on_update, name, sheet)

    def _save(self, name, assignment: Assignment, sheet):
        try:
            with assignment.file_lock:
                save_sheet(sheet, assignment.filepath)
        except OSError as exc:
            self._emit(self.on_error, name, f"Falha ao salvar {assignment.filepath}: {exc}")

    @staticmethod
    def _emit(callback, *args):
        if callback:
            try:
                callback(*args)
            except Exception:
                pass
