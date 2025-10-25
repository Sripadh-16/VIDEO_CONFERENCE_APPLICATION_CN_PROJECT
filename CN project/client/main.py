import sys
import os

# Ensure project root is on sys.path when executed as a script
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from PyQt6 import QtWidgets

from client.ui import ChatWindow


def main() -> None:
	app = QtWidgets.QApplication(sys.argv)
	window = ChatWindow()
	window.show()
	sys.exit(app.exec())


if __name__ == "__main__":
	main()
