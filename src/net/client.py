"""Cliente do jogador: conecta no mestre, recebe a ficha e reconecta sozinho se cair."""
import copy
import socket
import threading

from src.net.protocol import (DEFAULT_PORT, HEARTBEAT_INTERVAL, HEARTBEAT_TIMEOUT,
                              PROTOCOL_VERSION, Connection, ConnectionClosed)

# Estados informados em on_status(state, msg)
CONNECTING = "connecting"      # primeira tentativa
WAITING = "waiting"            # conectado, aguardando o mestre escolher a ficha
ONLINE = "online"              # com ficha, sincronizando
RECONNECTING = "reconnecting"  # caiu; tentando voltar (edições ficam guardadas)
CLOSED = "closed"              # fim (erro, expulso ou fechado pelo usuário)


class DNDClient:
    """Callbacks (chamados na thread de rede; a GUI deve repassar com root.after):
        on_status(state, msg), on_sheet(sheet)
    """

    def __init__(self, host, name, port=DEFAULT_PORT, heartbeat_interval=HEARTBEAT_INTERVAL,
                 heartbeat_timeout=HEARTBEAT_TIMEOUT, connect_timeout=5.0, max_backoff=10.0):
        self.host = host
        self.port = port
        self.name = name
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout
        self.connect_timeout = connect_timeout
        self.max_backoff = max_backoff

        self.on_status = None
        self.on_sheet = None

        self.state = CONNECTING
        self.system = None            # sistema da sessão, informado pelo mestre
        self._conn = None
        self._pending = None          # última ficha editada sem conexão
        self._lock = threading.Lock()
        self._stopped = threading.Event()
        self._thread = None

    # ------------------------------------------------------------------ API
    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def close(self):
        self._stopped.set()
        with self._lock:
            conn = self._conn
        if conn:
            conn.close()

    def send_update(self, sheet: dict):
        """Envia a ficha editada. Sem conexão, guarda para enviar quando reconectar."""
        snapshot = copy.deepcopy(sheet)
        with self._lock:
            conn = self._conn if self.state == ONLINE else None
            if conn is None or not conn.send({"type": "update", "sheet": snapshot}):
                self._pending = snapshot

    # ------------------------------------------------------------------ loop de rede
    def _set_state(self, state, msg=""):
        self.state = state
        if self.on_status:
            self.on_status(state, msg)

    def _run(self):
        accepted_once = False
        attempt = 0
        while not self._stopped.is_set():
            try:
                sock = socket.create_connection((self.host, self.port), timeout=self.connect_timeout)
            except OSError as exc:
                if not accepted_once:
                    self._set_state(CLOSED, f"Não foi possível conectar em {self.host}:{self.port} ({exc.strerror or exc}).")
                    return
                attempt += 1
                self._set_state(RECONNECTING, "Tentando reconectar...")
                self._stopped.wait(min(self.max_backoff, 1.0 * attempt))
                continue

            conn = Connection(sock, self.heartbeat_interval, self.heartbeat_timeout)
            with self._lock:
                self._conn = conn
            conn.send({"type": "login", "name": self.name, "version": PROTOCOL_VERSION})

            try:
                while True:
                    message = conn.recv()
                    kind = message.get("type")
                    if kind == "welcome":
                        accepted_once = True
                        attempt = 0
                        self.system = message.get("system")
                        if not message.get("assigned"):
                            self._set_state(WAITING, "Aguardando o mestre escolher sua ficha...")
                    elif kind == "sheet":
                        self._receive_sheet(conn, message.get("sheet"))
                    elif kind in ("error", "kicked"):
                        self._set_state(CLOSED, message.get("msg", "Conexão encerrada pelo mestre."))
                        self.close()
                        return
            except ConnectionClosed:
                pass
            finally:
                with self._lock:
                    if self._conn is conn:
                        self._conn = None

            if self._stopped.is_set():
                break
            if not accepted_once:
                self._set_state(CLOSED, "O mestre fechou a conexão.")
                return
            self._set_state(RECONNECTING, "Conexão perdida. Tentando reconectar...")
            self._stopped.wait(1.0)

        self._set_state(CLOSED, "")

    def _receive_sheet(self, conn, sheet):
        if not isinstance(sheet, dict):
            return
        with self._lock:
            pending, self._pending = self._pending, None
            was_online = self.state == ONLINE
            self.state = ONLINE
        if pending is not None and not was_online:
            # Voltou da queda com edições locais: elas valem mais que a cópia do servidor.
            if not conn.send({"type": "update", "sheet": pending}):
                with self._lock:
                    self._pending = pending
            self._set_state(ONLINE, "")
            return
        self._set_state(ONLINE, "")
        if self.on_sheet:
            self.on_sheet(sheet)
