import os
import socket
import threading
from typing import Dict, Tuple

from common.protocol import (
	CHAT,
	CHAT_BROADCAST,
	HELLO,
	USER_JOINED,
	USER_LEFT,
	ERROR,
	PING,
	PONG,
	REGISTER_AV,
	make_message,
	send_json_line,
	recv_json_lines,
)
from server.av_udp import VideoRelay, AudioMixerRelay
from server.screen_share import ScreenShareServer
from server.file_transfer import FileTransferServer


class ClientSession:
	def __init__(self, sock: socket.socket, address: Tuple[str, int]) -> None:
		self.sock = sock
		self.address = address
		self.username = ""
		self.buffer = bytearray()


class ControlServer:
	def __init__(self, host: str, port: int) -> None:
		self.host = host
		self.port = port
		self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.clients_lock = threading.Lock()
		self.clients: Dict[socket.socket, ClientSession] = {}
		self.running = False

		self.video_relay = VideoRelay(self.host)
		self.audio_relay = AudioMixerRelay(self.host)
		self.screen_share = ScreenShareServer(self.host)
		self.file_server = FileTransferServer(self.host, storage_dir=os.path.join("storage", "files"))

	def run(self) -> None:
		self.server_sock.bind((self.host, self.port))
		self.server_sock.listen(100)
		self.running = True
		print(f"Server listening on {self.host}:{self.port}")

		threading.Thread(target=self.video_relay.run, daemon=True).start()
		threading.Thread(target=self.audio_relay.run, daemon=True).start()
		threading.Thread(target=self.screen_share.run, daemon=True).start()
		threading.Thread(target=self.file_server.run, daemon=True).start()

		accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
		accept_thread.start()
		try:
			accept_thread.join()
		except KeyboardInterrupt:
			print("Shutting down server...")
		finally:
			self.shutdown()

	def shutdown(self) -> None:
		self.running = False
		with self.clients_lock:
			for s in list(self.clients.keys()):
				try:
					s.shutdown(socket.SHUT_RDWR)
					s.close()
				except OSError:
					pass
		self.server_sock.close()
		self.video_relay.stop()
		self.audio_relay.stop()
		self.screen_share.stop()
		self.file_server.stop()

	def _accept_loop(self) -> None:
		while self.running:
			try:
				client_sock, addr = self.server_sock.accept()
			except OSError:
				break
			client_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
			session = ClientSession(client_sock, addr)
			with self.clients_lock:
				self.clients[client_sock] = session
			threading.Thread(target=self._client_loop, args=(session,), daemon=True).start()

	def _remove_client(self, session: ClientSession) -> None:
		with self.clients_lock:
			if session.sock in self.clients:
				username = self.clients[session.sock].username
				del self.clients[session.sock]
				if username:
					self._broadcast(make_message(USER_LEFT, {"username": username}))
		try:
			session.sock.close()
		except OSError:
			pass

	def _broadcast(self, message: dict, exclude: socket.socket | None = None) -> None:
		with self.clients_lock:
			for s, sess in list(self.clients.items()):
				if exclude is not None and s is exclude:
					continue
				try:
					send_json_line(s, message)
				except OSError:
					pass

	def _client_loop(self, session: ClientSession) -> None:
		print(f"Client connected: {session.address}")
		try:
			while True:
				chunk = session.sock.recv(4096)
				if not chunk:
					break
				session.buffer.extend(chunk)
				while True:
					obj, session.buffer = recv_json_lines(session.buffer)
					if obj is None:
						break
					self._handle_message(session, obj)
		except OSError:
			pass
		finally:
			print(f"Client disconnected: {session.address}")
			self._remove_client(session)

	def _handle_message(self, session: ClientSession, msg: dict) -> None:
		type_ = msg.get("type")
		payload = msg.get("payload", {})
		if type_ == HELLO:
			username = str(payload.get("username", "")).strip()
			if not username:
				send_json_line(session.sock, make_message(ERROR, {"message": "Username required"}))
				return
			session.username = username
			self._broadcast(make_message(USER_JOINED, {"username": username}), exclude=None)
			return
		if type_ == CHAT:
			text = str(payload.get("text", ""))
			if not session.username:
				send_json_line(session.sock, make_message(ERROR, {"message": "Send HELLO first"}))
				return
			self._broadcast(
				make_message(CHAT_BROADCAST, {"username": session.username, "text": text}),
				exclude=None,
			)
			return
		if type_ == REGISTER_AV:
			v_port = int(payload.get("video_port", 0))
			a_port = int(payload.get("audio_port", 0))
			client_addr = session.sock.getpeername()
			if v_port:
				self.video_relay.register_client((client_addr[0], v_port), (client_addr[0], v_port))
			if a_port:
				self.audio_relay.register_client((client_addr[0], a_port), (client_addr[0], a_port))
			return
		if type_ == PING:
			send_json_line(session.sock, make_message(PONG, {}))
			return
		send_json_line(session.sock, make_message(ERROR, {"message": "Unknown type"}))
