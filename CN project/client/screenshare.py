import socket
import struct
import threading
from typing import Callable

from PIL import ImageGrab, Image
import io

from common.constants import SCREEN_TCP_PORT


class ScreenPresenter(threading.Thread):
	def __init__(self, server_ip: str) -> None:
		super().__init__(daemon=True)
		self.server_ip = server_ip
		self.running = True
		self.sock: socket.socket | None = None

	def run(self) -> None:
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock.connect((self.server_ip, SCREEN_TCP_PORT))
		self.sock.sendall(b"PRESENT")
		try:
			while self.running:
				img = ImageGrab.grab()
				buf = io.BytesIO()
				img = img.convert("RGB")
				img.save(buf, format="JPEG", quality=60)
				data = buf.getvalue()
				self.sock.sendall(struct.pack("!I", len(data)))
				self.sock.sendall(data)
		except OSError:
			pass
		finally:
			try:
				if self.sock:
					self.sock.close()
			except OSError:
				pass

	def stop(self) -> None:
		self.running = False
		try:
			if self.sock:
				self.sock.close()
		except OSError:
			pass


class ScreenViewer(threading.Thread):
	def __init__(self, server_ip: str, on_image: Callable[[Image.Image], None]) -> None:
		super().__init__(daemon=True)
		self.server_ip = server_ip
		self.on_image = on_image
		self.running = True
		self.sock: socket.socket | None = None

	def run(self) -> None:
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock.connect((self.server_ip, SCREEN_TCP_PORT))
		self.sock.sendall(b"VIEWER\n")
		try:
			while self.running:
				hdr = self._recv_exact(self.sock, 4)
				if not hdr:
					break
				(size,) = struct.unpack("!I", hdr)
				payload = self._recv_exact(self.sock, size)
				if not payload:
					break
				img = Image.open(io.BytesIO(payload))
				self.on_image(img)
		except OSError:
			pass
		finally:
			try:
				if self.sock:
					self.sock.close()
			except OSError:
				pass

	def _recv_exact(self, sock: socket.socket, size: int) -> bytes | None:
		buf = bytearray()
		while len(buf) < size:
			chunk = sock.recv(size - len(buf))
			if not chunk:
				return None
			buf.extend(chunk)
		return bytes(buf)

	def stop(self) -> None:
		self.running = False
		try:
			if self.sock:
				self.sock.close()
		except OSError:
			pass
