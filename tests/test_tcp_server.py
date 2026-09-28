import socket
import threading
import time

from server.tcp_server import TCPServer


def start_server():
    server = TCPServer(host="127.0.0.1", port=6380)

    thread = threading.Thread(target=server.start, daemon=True)
    thread.start()

    time.sleep(0.2)

    return server, thread


def send_command(command):
    with socket.create_connection(("127.0.0.1", 6380)) as client:
        client.sendall(command)
        return client.recv(4096)


def test_ping():
    server, _ = start_server()

    try:
        response = send_command(b"PING\r\n")
        assert response == b"+PONG\r\n"
    finally:
        server.stop()


def test_set_and_get():
    server, _ = start_server()

    try:
        set_response = send_command(b"SET name Jiya\r\n")
        assert set_response == b"+OK\r\n"

        get_response = send_command(b"GET name\r\n")
        assert get_response == b"$4\r\nJiya\r\n"
    finally:
        server.stop()


def test_delete():
    server, _ = start_server()

    try:
        send_command(b"SET name Jiya\r\n")

        response = send_command(b"DEL name\r\n")
        assert response == b":1\r\n"

        response = send_command(b"GET name\r\n")
        assert response == b"$-1\r\n"
    finally:
        server.stop()


def test_exists():
    server, _ = start_server()

    try:
        send_command(b"SET name Jiya\r\n")

        response = send_command(b"EXISTS name\r\n")
        assert response == b":1\r\n"
    finally:
        server.stop()