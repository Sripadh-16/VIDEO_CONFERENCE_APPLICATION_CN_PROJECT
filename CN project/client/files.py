import os
import socket
import struct

from common.constants import FILE_TCP_PORT


def upload_file(server_ip: str, path: str) -> bool:
	if not os.path.exists(path):
		return False
	try:
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.settimeout(10)  # 10 second timeout
		sock.connect((server_ip, FILE_TCP_PORT))
		try:
			sock.sendall(b"\x01")
			name_bytes = os.path.basename(path).encode("utf-8")
			sock.sendall(struct.pack("!H", len(name_bytes)))
			sock.sendall(name_bytes)
			size = os.path.getsize(path)
			sock.sendall(struct.pack("!Q", size))
			with open(path, "rb") as f:
				while True:
					chunk = f.read(65536)
					if not chunk:
						break
					sock.sendall(chunk)
			return True
		finally:
			try:
				sock.close()
			except OSError:
				pass
	except (OSError, socket.timeout) as e:
		print(f"Upload failed: {e}")
		return False


def download_file(server_ip: str, filename: str, dest_dir: str) -> bool:
	os.makedirs(dest_dir, exist_ok=True)
	try:
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.settimeout(10)  # 10 second timeout
		sock.connect((server_ip, FILE_TCP_PORT))
		try:
			sock.sendall(b"\x02")
			name_bytes = filename.encode("utf-8")
			sock.sendall(struct.pack("!H", len(name_bytes)))
			sock.sendall(name_bytes)
			size_bytes = _recv_exact(sock, 8)
			if not size_bytes:
				return False
			(size,) = struct.unpack("!Q", size_bytes)
			if size == 0:
				return False
			path = os.path.join(dest_dir, filename)
			remaining = size
			with open(path, "wb") as f:
				while remaining > 0:
					chunk = sock.recv(min(65536, remaining))
					if not chunk:
						break
					f.write(chunk)
					remaining -= len(chunk)
			return remaining == 0
		finally:
			try:
				sock.close()
			except OSError:
				pass
	except (OSError, socket.timeout) as e:
		print(f"Download failed: {e}")
		return False


def _recv_exact(sock: socket.socket, size: int) -> bytes | None:
	buf = bytearray()
	while len(buf) < size:
		chunk = sock.recv(size - len(buf))
		if not chunk:
			return None
		buf.extend(chunk)
	return bytes(buf)
