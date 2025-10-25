import socket
import struct
import threading
from typing import Optional, Callable

import cv2
import numpy as np
import sounddevice as sd

from common.constants import (
	VIDEO_UDP_PORT,
	AUDIO_UDP_PORT,
	VIDEO_WIDTH,
	VIDEO_HEIGHT,
	VIDEO_JPEG_QUALITY,
	AUDIO_SAMPLE_RATE,
	AUDIO_CHANNELS,
	AUDIO_CHUNK_MS,
)
from common.protocol import make_message, send_json_line, REGISTER_AV


class VideoSender(threading.Thread):
	def __init__(self, server_ip: str, username: str) -> None:
		super().__init__(daemon=True)
		self.server_addr = (server_ip, VIDEO_UDP_PORT)
		self.username = username.encode("utf-8")[:255]
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.cap = cv2.VideoCapture(0)
		self.running = True

	def run(self) -> None:
		name_len = len(self.username)
		prefix = bytes([name_len]) + self.username
		while self.running:
			ok, frame = self.cap.read()
			if not ok:
				continue
			frame = cv2.resize(frame, (VIDEO_WIDTH, VIDEO_HEIGHT))
			encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), VIDEO_JPEG_QUALITY]
			ok, enc = cv2.imencode('.jpg', frame, encode_param)
			if not ok:
				continue
			self.sock.sendto(prefix + enc.tobytes(), self.server_addr)

	def stop(self) -> None:
		self.running = False
		self.cap.release()
		self.sock.close()


class VideoReceiver(threading.Thread):
	def __init__(self, on_frame: Callable[[str, np.ndarray], None]) -> None:
		super().__init__(daemon=True)
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.sock.bind(("0.0.0.0", 0))
		self.on_frame = on_frame
		self.running = True

	@property
	def local_addr(self) -> tuple[str, int]:
		return self.sock.getsockname()

	def run(self) -> None:
		while self.running:
			data, _ = self.sock.recvfrom(65535)
			if not data:
				continue
			name_len = data[0]
			name = data[1:1+name_len].decode('utf-8', errors='ignore')
			jpeg = data[1+name_len:]
			arr = np.frombuffer(jpeg, dtype=np.uint8)
			frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
			if frame is not None:
				self.on_frame(name, frame)

	def stop(self) -> None:
		self.running = False
		self.sock.close()


class AudioSender(threading.Thread):
	def __init__(self, server_ip: str) -> None:
		super().__init__(daemon=True)
		self.server_addr = (server_ip, AUDIO_UDP_PORT)
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.running = True
		self.blocksize = int(AUDIO_SAMPLE_RATE * AUDIO_CHUNK_MS / 1000)

	def _callback(self, indata, frames, time, status):
		if not self.running:
			return
		pcm16 = (indata[:, 0] * 32767.0).astype(np.int16).tobytes()
		self.sock.sendto(pcm16, self.server_addr)

	def run(self) -> None:
		with sd.InputStream(samplerate=AUDIO_SAMPLE_RATE, channels=AUDIO_CHANNELS, callback=self._callback, blocksize=self.blocksize):
			while self.running:
				sd.sleep(100)

	def stop(self) -> None:
		self.running = False
		self.sock.close()


class AudioReceiver(threading.Thread):
	def __init__(self, control_sock: socket.socket) -> None:
		super().__init__(daemon=True)
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.sock.bind(("0.0.0.0", 0))
		self.running = True
		self.blocksize = int(AUDIO_SAMPLE_RATE * AUDIO_CHUNK_MS / 1000)
		self.control_sock = control_sock

	@property
	def local_addr(self) -> tuple[str, int]:
		return self.sock.getsockname()

	def run(self) -> None:
		# register local ports for server-side relays
		msg = make_message(REGISTER_AV, {"video_port": 0, "audio_port": self.local_addr[1]})
		send_json_line(self.control_sock, msg)
		with sd.OutputStream(samplerate=AUDIO_SAMPLE_RATE, channels=AUDIO_CHANNELS, dtype='int16', blocksize=self.blocksize) as stream:
			while self.running:
				data, _ = self.sock.recvfrom(65535)
				stream.write(np.frombuffer(data, dtype=np.int16).reshape(-1, 1))

	def stop(self) -> None:
		self.running = False
		self.sock.close()
