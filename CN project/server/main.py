import argparse
import os
import sys

# Ensure project root is on sys.path when executed as a script
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from server_core import ControlServer


def main() -> None:
	parser = argparse.ArgumentParser(description="LAN Collaboration Server")
	parser.add_argument("--host", default="0.0.0.0")
	parser.add_argument("--port", type=int, default=5000)
	args = parser.parse_args()

	server = ControlServer(args.host, args.port)
	server.run()


if __name__ == "__main__":
	main()
