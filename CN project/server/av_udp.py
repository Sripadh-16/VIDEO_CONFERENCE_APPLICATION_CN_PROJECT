import socket
import struct
import threading
from typing import Dict, Tuple, Optional

from common.constants import VIDEO_UDP_PORT, AUDIO_UDP_PORT, AUDIO_SAMPLE_RATE, AUDIO_CHANNELS
import numpy as np


class VideoRelay:
	def __init__(self, host: str) -> None:
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.sock.bind((host, VIDEO_UDP_PORT))
		self.running = False
		self.clients_lock = threading.Lock()
		self.clients: Dict[Tuple[str, int], Tuple[str, int]] = {}

	def register_client(self, client_control_addr: Tuple[str, int], video_recv_addr: Tuple[str, int]) -> None:
		with self.clients_lock:
			self.clients[client_control_addr] = video_recv_addr

	def unregister_client(self, client_control_addr: Tuple[str, int]) -> None:
		with self.clients_lock:
			self.clients.pop(client_control_addr, None)

	def run(self) -> None:
		self.running = True
		while self.running:
			data, addr = self.sock.recvfrom(65535)
			# data format: [name_len u8][name bytes][jpeg...]
			if not data:
				continue
			name_len = data[0]
			name = data[1:1+name_len]
			jpeg = data[1+name_len:]
			packet = bytes([name_len]) + name + jpeg
			with self.clients_lock:
				targets = [v for k, v in self.clients.items() if k != addr]
			for t in targets:
				self.sock.sendto(packet, t)

	def stop(self) -> None:
		self.running = False
		self.sock.close()


class AudioMixerRelay:
	def __init__(self, host: str) -> None:
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.sock.bind((host, AUDIO_UDP_PORT))
		self.running = False
		self.clients_lock = threading.Lock()
		self.clients: Dict[Tuple[str, int], Tuple[str, int]] = {}

	def register_client(self, client_control_addr: Tuple[str, int], audio_recv_addr: Tuple[str, int]) -> None:
		with self.clients_lock:
			self.clients[client_control_addr] = audio_recv_addr

	def unregister_client(self, client_control_addr: Tuple[str, int]) -> None:
		with self.clients_lock:
			self.clients.pop(client_control_addr, None)

	def run(self) -> None:
		self.running = True
		# Mix frames arriving sequentially by summing per-sample with clipping, rebroadcasting to all.
		while self.running:
			data, addr = self.sock.recvfrom(65535)
			with self.clients_lock:
				targets = list(self.clients.values())
			# naive: forward the most recent packet as "mixed"; for real mixing we'd buffer by timestamps
			for t in targets:
				self.sock.sendto(data, t)

	def stop(self) -> None:
		self.running = False
		self.sock.close()
