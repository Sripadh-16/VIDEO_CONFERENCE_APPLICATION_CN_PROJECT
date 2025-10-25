import socket
import threading
from typing import Optional

from common.protocol import make_message, send_json_line, recv_json_lines, HELLO


class ClientThread(threading.Thread):
	def __init__(self, window) -> None:
		super().__init__(daemon=True)
		self.window = window
		self.sock: Optional[socket.socket] = None
		self.buffer = bytearray()
		self.running = True

	def connect_to_server(self, host: str, port: int, username: str) -> None:
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock.connect((host, port))
		self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
		send_json_line(self.sock, make_message(HELLO, {"username": username}))

	def run(self) -> None:
		if self.sock is None:
			return
		try:
			while self.running:
				chunk = self.sock.recv(4096)
				if not chunk:
					break
				self.buffer.extend(chunk)
				while True:
					obj, self.buffer = recv_json_lines(self.buffer)
					if obj is None:
						break
					self.window.handle_server_message(obj)
		except OSError:
			pass
		finally:
			self.window.on_disconnected()

	def send_chat(self, text: str) -> None:
		if self.sock is None:
			return
		from common.protocol import CHAT
		send_json_line(self.sock, make_message(CHAT, {"text": text}))

	def close(self) -> None:
		self.running = False
		try:
			if self.sock:
				self.sock.shutdown(socket.SHUT_RDWR)
				self.sock.close()
		except OSError:
			pass
