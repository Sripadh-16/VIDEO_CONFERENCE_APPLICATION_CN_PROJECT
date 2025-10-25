from PyQt6 import QtCore, QtGui, QtWidgets
from typing import Optional, Dict

from common.protocol import CHAT_BROADCAST, USER_JOINED, USER_LEFT, ERROR
from client.net import ClientThread
from client.av import VideoSender, VideoReceiver, AudioSender, AudioReceiver
from client.screenshare import ScreenPresenter, ScreenViewer
from client.files import upload_file, download_file


class ChatWindow(QtWidgets.QWidget):
	def __init__(self) -> None:
		super().__init__()
		self.setWindowTitle("LAN Collaboration Client")

		self.server_ip = QtWidgets.QLineEdit()
		self.server_ip.setPlaceholderText("Server IP e.g. 192.168.1.10")
		self.server_port = QtWidgets.QLineEdit()
		self.server_port.setPlaceholderText("Port e.g. 5000")
		self.username = QtWidgets.QLineEdit()
		self.username.setPlaceholderText("Username")
		self.connect_btn = QtWidgets.QPushButton("Connect")

		self.tabs = QtWidgets.QTabWidget()
		self._build_chat_tab()
		self._build_audio_tab()
		self._build_video_tab()
		self._build_screen_tab()
		self._build_files_tab()

		layout = QtWidgets.QVBoxLayout()
		top_form = QtWidgets.QHBoxLayout()
		top_form.addWidget(self.server_ip)
		top_form.addWidget(self.server_port)
		top_form.addWidget(self.username)
		top_form.addWidget(self.connect_btn)
		layout.addLayout(top_form)
		layout.addWidget(self.tabs)
		self.setLayout(layout)

		self.thread: Optional[ClientThread] = None
		self.video_sender: Optional[VideoSender] = None
		self.video_receiver: Optional[VideoReceiver] = None
		self.audio_sender: Optional[AudioSender] = None
		self.audio_receiver: Optional[AudioReceiver] = None
		self.presenter: Optional[ScreenPresenter] = None
		self.viewer: Optional[ScreenViewer] = None

		self.video_views: Dict[str, QtWidgets.QLabel] = {}

		self.connect_btn.clicked.connect(self.on_connect)
		self.send_btn.clicked.connect(self.on_send)
		self.start_audio_btn.clicked.connect(self.on_start_audio)
		self.stop_audio_btn.clicked.connect(self.on_stop_audio)
		self.start_av_btn.clicked.connect(self.on_start_av)
		self.stop_av_btn.clicked.connect(self.on_stop_av)
		self.start_present_btn.clicked.connect(self.on_start_present)
		self.stop_present_btn.clicked.connect(self.on_stop_present)
		self.start_view_btn.clicked.connect(self.on_start_view)
		self.stop_view_btn.clicked.connect(self.on_stop_view)
		self.upload_btn.clicked.connect(self.on_upload)
		self.download_btn.clicked.connect(self.on_download)

	def _build_chat_tab(self) -> None:
		self.chat_view = QtWidgets.QTextEdit()
		self.chat_view.setReadOnly(True)
		self.chat_input = QtWidgets.QLineEdit()
		self.send_btn = QtWidgets.QPushButton("Send")
		self.send_btn.setEnabled(False)

		chat_tab = QtWidgets.QWidget()
		v = QtWidgets.QVBoxLayout(chat_tab)
		v.addWidget(self.chat_view)
		h = QtWidgets.QHBoxLayout()
		h.addWidget(self.chat_input)
		h.addWidget(self.send_btn)
		v.addLayout(h)
		self.tabs.addTab(chat_tab, "Chat")

	def _build_audio_tab(self) -> None:
		self.start_audio_btn = QtWidgets.QPushButton("Start Audio Chat")
		self.stop_audio_btn = QtWidgets.QPushButton("Stop Audio Chat")
		self.stop_audio_btn.setEnabled(False)
		
		self.audio_status = QtWidgets.QLabel("Audio chat is not active")
		self.audio_status.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
		self.audio_status.setStyleSheet("padding: 20px; border: 1px solid gray; background-color: #f0f0f0;")

		audio_tab = QtWidgets.QWidget()
		v = QtWidgets.QVBoxLayout(audio_tab)
		v.addWidget(self.audio_status)
		h = QtWidgets.QHBoxLayout()
		h.addWidget(self.start_audio_btn)
		h.addWidget(self.stop_audio_btn)
		v.addLayout(h)
		self.tabs.addTab(audio_tab, "Audio Chat")

	def _build_video_tab(self) -> None:
		self.video_grid = QtWidgets.QGridLayout()
		self.start_av_btn = QtWidgets.QPushButton("Start A/V")
		self.stop_av_btn = QtWidgets.QPushButton("Stop A/V")

		video_tab = QtWidgets.QWidget()
		v = QtWidgets.QVBoxLayout(video_tab)
		container = QtWidgets.QWidget()
		container.setLayout(self.video_grid)
		scroll = QtWidgets.QScrollArea()
		scroll.setWidgetResizable(True)
		scroll.setWidget(container)
		v.addWidget(scroll)
		h = QtWidgets.QHBoxLayout()
		h.addWidget(self.start_av_btn)
		h.addWidget(self.stop_av_btn)
		v.addLayout(h)
		self.tabs.addTab(video_tab, "Video/Audio")

	def _build_screen_tab(self) -> None:
		self.screen_label = QtWidgets.QLabel()
		self.screen_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
		self.screen_label.setFixedSize(800, 600)  # Set fixed size to prevent expansion
		self.screen_label.setStyleSheet("border: 1px solid gray; background-color: black;")
		self.start_present_btn = QtWidgets.QPushButton("Start Presenting")
		self.stop_present_btn = QtWidgets.QPushButton("Stop Presenting")
		self.start_view_btn = QtWidgets.QPushButton("Start Viewing")
		self.stop_view_btn = QtWidgets.QPushButton("Stop Viewing")
		
		# Initialize button states
		self.stop_present_btn.setEnabled(False)
		self.stop_view_btn.setEnabled(False)

		screen_tab = QtWidgets.QWidget()
		v = QtWidgets.QVBoxLayout(screen_tab)
		v.addWidget(self.screen_label)
		h1 = QtWidgets.QHBoxLayout()
		h1.addWidget(self.start_present_btn)
		h1.addWidget(self.stop_present_btn)
		v.addLayout(h1)
		h2 = QtWidgets.QHBoxLayout()
		h2.addWidget(self.start_view_btn)
		h2.addWidget(self.stop_view_btn)
		v.addLayout(h2)
		self.tabs.addTab(screen_tab, "Screen Share")

	def _build_files_tab(self) -> None:
		self.upload_btn = QtWidgets.QPushButton("Upload File...")
		self.download_name = QtWidgets.QLineEdit()
		self.download_name.setPlaceholderText("Filename to download")
		self.download_btn = QtWidgets.QPushButton("Download")

		files_tab = QtWidgets.QWidget()
		v = QtWidgets.QVBoxLayout(files_tab)
		v.addWidget(self.upload_btn)
		h = QtWidgets.QHBoxLayout()
		h.addWidget(self.download_name)
		h.addWidget(self.download_btn)
		v.addLayout(h)
		self.tabs.addTab(files_tab, "Files")

	def on_connect(self) -> None:
		host = self.server_ip.text().strip()
		port_text = self.server_port.text().strip()
		username = self.username.text().strip()
		if not host or not port_text or not username:
			self.append_line("[system] Enter server IP, port, and username")
			return
		try:
			port = int(port_text)
		except ValueError:
			self.append_line("[system] Invalid port")
			return
		self.thread = ClientThread(self)
		try:
			self.thread.connect_to_server(host, port, username)
		except OSError as e:
			self.append_line(f"[system] Connection failed: {e}")
			self.thread = None
			return
		self.thread.start()
		self.connect_btn.setEnabled(False)
		self.send_btn.setEnabled(True)
		self.append_line(f"[system] Connected to {host}:{port}")

	def on_send(self) -> None:
		text = self.chat_input.text().strip()
		if not text or self.thread is None:
			return
		self.thread.send_chat(text)
		self.chat_input.clear()

	def on_start_audio(self) -> None:
		if self.audio_sender is None and self.audio_receiver is None:
			server_ip = self.server_ip.text().strip()
			if not server_ip:
				self.append_line("[audio] Enter server IP first")
				return
			
			if self.thread is None:
				self.append_line("[audio] Connect to server first")
				return
			
			# Start audio receiver first
			if self.audio_receiver is None:
				self.audio_receiver = AudioReceiver(self.thread.sock)  # type: ignore[arg-type]
				self.audio_receiver.start()
			
			# Start audio sender
			if self.audio_sender is None:
				self.audio_sender = AudioSender(server_ip)
				self.audio_sender.start()
			
			self.append_line("[audio] Audio chat started")
			self.audio_status.setText("Audio chat is active - You can speak now!")
			self.audio_status.setStyleSheet("padding: 20px; border: 1px solid green; background-color: #e8f5e8;")
			self.start_audio_btn.setEnabled(False)
			self.stop_audio_btn.setEnabled(True)

	def on_stop_audio(self) -> None:
		if self.audio_sender:
			self.audio_sender.stop()
			self.audio_sender = None
		if self.audio_receiver:
			self.audio_receiver.stop()
			self.audio_receiver = None
		
		self.append_line("[audio] Audio chat stopped")
		self.audio_status.setText("Audio chat is not active")
		self.audio_status.setStyleSheet("padding: 20px; border: 1px solid gray; background-color: #f0f0f0;")
		self.start_audio_btn.setEnabled(True)
		self.stop_audio_btn.setEnabled(False)

	def on_start_av(self) -> None:
		if self.video_receiver is None:
			self.video_receiver = VideoReceiver(self._on_video_frame)
			self.video_receiver.start()
			# register video receive port
			from common.protocol import make_message, send_json_line, REGISTER_AV
			msg = make_message(REGISTER_AV, {"video_port": self.video_receiver.local_addr[1], "audio_port": 0})
			send_json_line(self.thread.sock, msg)  # type: ignore[attr-defined]
		if self.audio_receiver is None:
			self.audio_receiver = AudioReceiver(self.thread.sock)  # type: ignore[arg-type]
			self.audio_receiver.start()
		host = self.server_ip.text().strip()
		if self.video_sender is None:
			self.video_sender = VideoSender(host, self.username.text().strip())
			self.video_sender.start()
		if self.audio_sender is None:
			self.audio_sender = AudioSender(host)
			self.audio_sender.start()

	def on_stop_av(self) -> None:
		if self.video_sender:
			self.video_sender.stop()
			self.video_sender = None
		if self.audio_sender:
			self.audio_sender.stop()
			self.audio_sender = None
		if self.video_receiver:
			self.video_receiver.stop()
			self.video_receiver = None
		if self.audio_receiver:
			self.audio_receiver.stop()
			self.audio_receiver = None
		self._clear_video_grid()

	def _on_video_frame(self, name, frame) -> None:
		label = self.video_views.get(name)
		if label is None:
			label = QtWidgets.QLabel()
			label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
			self.video_views[name] = label
			self._relayout_grid()
		# update pixmap
		h, w, ch = frame.shape
		bytes_per_line = ch * w
		qimg = QtGui.QImage(frame.data, w, h, bytes_per_line, QtGui.QImage.Format.Format_BGR888)
		pix = QtGui.QPixmap.fromImage(qimg)
		def set_pix():
			label.setPixmap(pix)
		QtCore.QMetaObject.invokeMethod(self, "_noop", QtCore.Qt.ConnectionType.QueuedConnection)
		QtCore.QTimer.singleShot(0, set_pix)

	@QtCore.pyqtSlot()
	def _noop(self) -> None:
		pass

	def _relayout_grid(self) -> None:
		# simple grid placement
		for i in reversed(range(self.video_grid.count())):
			item = self.video_grid.itemAt(i)
			self.video_grid.removeItem(item)
		row = col = 0
		cols = 2
		for name, label in self.video_views.items():
			self.video_grid.addWidget(QtWidgets.QLabel(name), row, col)
			self.video_grid.addWidget(label, row+1, col)
			col += 1
			if col >= cols:
				col = 0
				row += 2

	def _clear_video_grid(self) -> None:
		self.video_views.clear()
		while self.video_grid.count():
			item = self.video_grid.takeAt(0)
			w = item.widget()
			if w:
				w.setParent(None)

	def on_start_present(self) -> None:
		if self.presenter is None:
			server_ip = self.server_ip.text().strip()
			if not server_ip:
				self.append_line("[screen] Enter server IP first")
				return
			self.presenter = ScreenPresenter(server_ip)
			self.presenter.start()
			self.append_line("[screen] Started presenting")
			self.start_present_btn.setEnabled(False)
			self.stop_present_btn.setEnabled(True)

	def on_stop_present(self) -> None:
		if self.presenter:
			self.presenter.stop()
			self.presenter = None
			self.append_line("[screen] Stopped presenting")
			self.start_present_btn.setEnabled(True)
			self.stop_present_btn.setEnabled(False)

	def on_start_view(self) -> None:
		if self.viewer is None:
			server_ip = self.server_ip.text().strip()
			if not server_ip:
				self.append_line("[screen] Enter server IP first")
				return
			self.viewer = ScreenViewer(server_ip, self._on_screen_image)
			self.viewer.start()
			self.append_line("[screen] Started viewing")
			self.start_view_btn.setEnabled(False)
			self.stop_view_btn.setEnabled(True)

	def on_stop_view(self) -> None:
		if self.viewer:
			self.viewer.stop()
			self.viewer = None
			self.append_line("[screen] Stopped viewing")
			self.start_view_btn.setEnabled(True)
			self.stop_view_btn.setEnabled(False)

	def _on_screen_image(self, pil_img) -> None:
		img = pil_img.convert("RGB")
		data = img.tobytes("raw", "RGB")
		w, h = img.size
		qimg = QtGui.QImage(data, w, h, QtGui.QImage.Format.Format_RGB888)
		pix = QtGui.QPixmap.fromImage(qimg)
		
		# Scale the image to fit the label while maintaining aspect ratio
		# Set a maximum size to prevent the window from becoming too large
		max_width = 800
		max_height = 600
		
		if w > max_width or h > max_height:
			# Calculate scaling factor to fit within max dimensions
			scale_w = max_width / w
			scale_h = max_height / h
			scale = min(scale_w, scale_h)
			
			new_w = int(w * scale)
			new_h = int(h * scale)
			pix = pix.scaled(new_w, new_h, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)
		
		QtCore.QMetaObject.invokeMethod(
			self.screen_label,
			"setPixmap",
			QtCore.Qt.ConnectionType.QueuedConnection,
			QtCore.Q_ARG(QtGui.QPixmap, pix),
		)

	def on_upload(self) -> None:
		path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select file to upload")
		if not path:
			return
		host = self.server_ip.text().strip()
		if not host:
			self.append_line("[files] Enter server IP first")
			return
		ok = upload_file(host, path)
		self.append_line("[files] Upload ok" if ok else "[files] Upload failed - check server is running")

	def on_download(self) -> None:
		name = self.download_name.text().strip()
		if not name:
			return
		host = self.server_ip.text().strip()
		if not host:
			self.append_line("[files] Enter server IP first")
			return
		ok = download_file(host, name, dest_dir="downloads")
		self.append_line("[files] Download ok" if ok else "[files] Download failed - check server is running")

	def handle_server_message(self, msg: dict) -> None:
		type_ = msg.get("type")
		payload = msg.get("payload", {})
		if type_ == CHAT_BROADCAST:
			self.append_line(f"{payload.get('username')}: {payload.get('text')}")
			return
		if type_ == USER_JOINED:
			self.append_line(f"[join] {payload.get('username')}")
			return
		if type_ == USER_LEFT:
			self.append_line(f"[leave] {payload.get('username')}")
			return
		if type_ == ERROR:
			self.append_line(f"[error] {payload.get('message')}")
			return

	def append_line(self, text: str) -> None:
		QtCore.QMetaObject.invokeMethod(
			self.chat_view,
			"append",
			QtCore.Qt.ConnectionType.QueuedConnection,
			QtCore.Q_ARG(str, text),
		)

	def on_disconnected(self) -> None:
		self.append_line("[system] Disconnected")
		self.connect_btn.setEnabled(True)
		self.send_btn.setEnabled(False)
