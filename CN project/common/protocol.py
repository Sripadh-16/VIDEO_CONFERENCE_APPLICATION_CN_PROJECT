import json
import socket
from typing import Any, Dict, Optional, Tuple

ENCODING = "utf-8"
BUFFER_SIZE = 65536

# Control message types (JSON line delimited over TCP)
HELLO = "HELLO"  # payload: {"username": str}
WELCOME = "WELCOME"  # payload: {"message": str}
CHAT = "CHAT"  # payload: {"text": str}
CHAT_BROADCAST = "CHAT_BROADCAST"  # payload: {"username": str, "text": str}
USER_JOINED = "USER_JOINED"  # payload: {"username": str}
USER_LEFT = "USER_LEFT"  # payload: {"username": str}
ERROR = "ERROR"  # payload: {"message": str}
PING = "PING"
PONG = "PONG"
REGISTER_AV = "REGISTER_AV"  # payload: {"video_port": int, "audio_port": int}
FILE_AVAILABLE = "FILE_AVAILABLE"  # payload: {"filename": str, "size": int}
PRESENTER_STATUS = "PRESENTER_STATUS"  # payload: {"active": bool}

LINE_SEP = "\n"


def send_json_line(sock: socket.socket, message: Dict[str, Any]) -> None:
	data = (json.dumps(message) + LINE_SEP).encode(ENCODING)
	view = memoryview(data)
	while view:
		sent = sock.send(view)
		view = view[sent:]


def recv_json_lines(buffer: bytearray) -> Tuple[Optional[Dict[str, Any]], bytearray]:
	"""Extract one JSON object from buffer if a full line exists; return (obj, new_buffer)."""
	idx = buffer.find(ord("\n"))
	if idx == -1:
		return None, buffer
	line = buffer[:idx].decode(ENCODING)
	rest = buffer[idx + 1 :]
	if not line:
		return None, rest
	try:
		obj = json.loads(line)
		return obj, rest
	except json.JSONDecodeError:
		return {"type": ERROR, "payload": {"message": "Malformed JSON"}}, rest


def make_message(msg_type: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
	return {"type": msg_type, "payload": payload or {}}
