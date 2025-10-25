import os
import socket
import struct
import threading
from typing import Dict, Tuple

from common.constants import FILE_TCP_PORT


class FileTransferServer:
	def __init__(self, host: str, storage_dir: str) -> None:
		self.host = host
		self.port = FILE_TCP_PORT
		self.storage_dir = storage_dir
		os.makedirs(self.storage_dir, exist_ok=True)
		self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.running = False

	def run(self) -> None:
		self.server.bind((self.host, self.port))
		self.server.listen(50)
		self.running = True
		while self.running:
			client, _ = self.server.accept()
			client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
			threading.Thread(target=self._client_loop, args=(client,), daemon=True).start()

	def stop(self) -> None:
		self.running = False
		try:
			self.server.close()
		except OSError:
			pass

	def _client_loop(self, sock: socket.socket) -> None:
		# Protocol: 1 byte op: 0x01 upload, 0x02 download
		try:
			op = sock.recv(1)
			if not op:
				return
			if op == b"\x01":
				self._handle_upload(sock)
			elif op == b"\x02":
				self._handle_download(sock)
			else:
				sock.close()
		except OSError:
			pass
		finally:
			try:
				sock.close()
			except OSError:
				pass

	def _handle_upload(self, sock: socket.socket) -> None:
		# [name_len u16][name bytes][size u64][data]
		name_len_bytes = self._recv_exact(sock, 2)
		if not name_len_bytes:
			return
		(name_len,) = struct.unpack("!H", name_len_bytes)
		name = self._recv_exact(sock, name_len)
		size_bytes = self._recv_exact(sock, 8)
		if not size_bytes:
			return
		(size,) = struct.unpack("!Q", size_bytes)
		filename = os.path.basename(name.decode("utf-8"))
		path = os.path.join(self.storage_dir, filename)
		remaining = size
		with open(path, "wb") as f:
			while remaining > 0:
				chunk = sock.recv(min(65536, remaining))
				if not chunk:
					break
				f.write(chunk)
				remaining -= len(chunk)

	def _handle_download(self, sock: socket.socket) -> None:
		# [name_len u16][name bytes]
		name_len_bytes = self._recv_exact(sock, 2)
		if not name_len_bytes:
			return
		(name_len,) = struct.unpack("!H", name_len_bytes)
		name = self._recv_exact(sock, name_len)
		filename = os.path.basename(name.decode("utf-8"))
		path = os.path.join(self.storage_dir, filename)
		if not os.path.exists(path):
			sock.sendall(struct.pack("!Q", 0))
			return
		size = os.path.getsize(path)
		sock.sendall(struct.pack("!Q", size))
		with open(path, "rb") as f:
			while True:
				chunk = f.read(65536)
				if not chunk:
					break
				sock.sendall(chunk)

	def _recv_exact(self, sock: socket.socket, size: int) -> bytes | None:
		buf = bytearray()
		while len(buf) < size:
			chunk = sock.recv(size - len(buf))
			if not chunk:
				return None
			buf.extend(chunk)
		return bytes(buf)
