## LAN Collaboration Suite (Server + Client)

A local-network-only, multi-user collaboration app in Python. Currently includes:
- Central server managing TCP control connections and group chat broadcast
- PyQt6 client with connect UI and real-time group text chat
- Placeholders for audio/video (UDP), screen share (TCP), and file transfer (TCP)

### Quick Start (Windows)

1) Create and activate a venv
```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

2) Start the server
```bash
python server/main.py --host 0.0.0.0 --port 5000
```

3) Start a client (on each participant machine)
```bash
python client/main.py
```
Enter the server IP and your username, then Connect.

### Roadmap
- UDP video/audio capture, encode, relay, and playback
- Screen share over TCP with presenter control
- File upload/download with progress
- Mixed audio on server and low-latency playback on client

### Repository Layout
- `server/`: server entrypoint and core
- `client/`: PyQt6 client app
- `common/`: shared protocol helpers

### Protocol (control channel)
JSON lines over TCP. Example message:
```json
{"type":"CHAT","payload":{"text":"hello"}}
```
Server broadcasts as `CHAT_BROADCAST` with `username` and `text`.

### License
MIT
