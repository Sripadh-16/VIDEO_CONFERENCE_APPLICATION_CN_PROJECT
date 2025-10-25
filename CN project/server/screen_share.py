import socket
import struct
import threading
from typing import Dict, Optional, Tuple

from common.constants import SCREEN_TCP_PORT


class ScreenShareServer:
	def __init__(self, host: str) -> None:
		self.host = host
		self.port = SCREEN_TCP_PORT
		self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.presenter_lock = threading.Lock()
		self.presenter: Optional[socket.socket] = None
		self.viewers_lock = threading.Lock()
		self.viewers: Dict[socket.socket, Tuple[str, int]] = {}
		self.running = False

	def run(self) -> None:
		self.server.bind((self.host, self.port))
		self.server.listen(50)
		self.running = True
		while self.running:
			client, addr = self.server.accept()
			client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
			threading.Thread(target=self._client_loop, args=(client,), daemon=True).start()

	def stop(self) -> None:
		self.running = False
		try:
			self.server.close()
		except OSError:
			pass

	def _client_loop(self, sock: socket.socket) -> None:
		try:
			role_hdr = sock.recv(7)
			if role_hdr == b"PRESENT":
				self._presenter_loop(sock)
				return
			elif role_hdr == b"VIEWER\n":
				with self.viewers_lock:
					self.viewers[sock] = sock.getpeername()
				self._viewer_wait(sock)
				return
			else:
				sock.close()
				return
		except OSError:
			try:
				sock.close()
			except OSError:
				pass

	def _presenter_loop(self, sock: socket.socket) -> None:
		with self.presenter_lock:
			if self.presenter is not None:
				sock.close()
				return
			self.presenter = sock
		try:
			while True:
				len_hdr = sock.recv(4)
				if len(len_hdr) < 4:
					break
				(frame_len,) = struct.unpack("!I", len_hdr)
				buf = bytearray()
				while len(buf) < frame_len:
					chunk = sock.recv(min(65536, frame_len - len(buf)))
					if not chunk:
						break
					buf.extend(chunk)
				if len(buf) != frame_len:
					break
				self._broadcast_frame(bytes(buf))
		except OSError:
			pass
		finally:
			with self.presenter_lock:
				self.presenter = None
			try:
				sock.close()
			except OSError:
				pass

	def _viewer_wait(self, sock: socket.socket) -> None:
		try:
			while True:
				data = sock.recv(1)
				if not data:
					break
		except OSError:
			pass
		finally:
			with self.viewers_lock:
				self.viewers.pop(sock, None)
			try:
				sock.close()
			except OSError:
				pass

	def _broadcast_frame(self, frame: bytes) -> None:
		packet = struct.pack("!I", len(frame)) + frame
		with self.viewers_lock:
			for s in list(self.viewers.keys()):
				try:
					s.sendall(packet)
				except OSError:
					self.viewers.pop(s, None)
