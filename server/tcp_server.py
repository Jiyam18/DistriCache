"""
TCP server for DistriCache.

Supports:
- Inline commands: SET foo bar
- RESP commands: *3\\r\\n$3\\r\\nSET...
"""

import socket
import threading

from core.store import Store, KeyNotFound
from server.protocol import (
    ProtocolError,
    parse_command,
    encode_simple_string,
    encode_error,
    encode_integer,
    encode_bulk_string,
)


class TCPServer:
    def __init__(self, host="127.0.0.1", port=6379, capacity=10_000):
        self.host = host
        self.port = port
        self.store = Store(capacity=capacity)
        self._server_socket = None
        self._running = False

    def start(self):
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((self.host, self.port))
        self._server_socket.listen()

        self._running = True

        print(f"DistriCache TCP server listening on {self.host}:{self.port}")

        while self._running:
            try:
                client_socket, address = self._server_socket.accept()
            except OSError:
                break

            thread = threading.Thread(
                target=self._handle_client,
                args=(client_socket, address),
                daemon=True,
            )
            thread.start()

    def stop(self):
        self._running = False

        if self._server_socket:
            self._server_socket.close()
            self._server_socket = None

    def _handle_client(self, client_socket, address):
        buffer = b""

        try:
            while self._running:
                data = client_socket.recv(4096)

                if not data:
                    break

                buffer += data

                while buffer:
                    try:
                        result = parse_command(buffer)
                    except ProtocolError as exc:
                        client_socket.sendall(encode_error(str(exc)))
                        return

                    if result.command is None:
                        break

                    buffer = buffer[result.bytes_consumed:]

                    if not result.command:
                        continue

                    response = self._execute_command(result.command)
                    client_socket.sendall(response)

        except ConnectionError:
            pass
        finally:
            client_socket.close()

    def _execute_command(self, command):
        name = command[0].upper()
        args = command[1:]

        try:
            if name == "PING":
                return encode_simple_string("PONG")

            if name == "GET":
                if len(args) != 1:
                    return encode_error("GET requires 1 argument")

                try:
                    value = self.store.get(args[0])
                except KeyNotFound:
                    return encode_bulk_string(None)

                return encode_bulk_string(str(value))

            if name == "SET":
                if len(args) != 2:
                    return encode_error("SET requires 2 arguments")

                self.store.set(args[0], args[1])
                return encode_simple_string("OK")

            if name == "DEL":
                if len(args) != 1:
                    return encode_error("DEL requires 1 argument")

                deleted = self.store.delete(args[0])
                return encode_integer(1 if deleted else 0)

            if name == "EXISTS":
                if len(args) != 1:
                    return encode_error("EXISTS requires 1 argument")

                return encode_integer(1 if self.store.exists(args[0]) else 0)

            if name == "EXPIRE":
                if len(args) != 2:
                    return encode_error("EXPIRE requires 2 arguments")

                seconds = float(args[1])
                result = self.store.expire(args[0], seconds)
                return encode_integer(1 if result else 0)

            if name == "TTL":
                if len(args) != 1:
                    return encode_error("TTL requires 1 argument")

                try:
                    ttl = self.store.ttl(args[0])
                except KeyNotFound:
                    return encode_integer(-2)

                if ttl is None:
                    return encode_integer(-1)

                return encode_integer(int(ttl))

            if name == "DBSIZE":
                if args:
                    return encode_error("DBSIZE takes no arguments")

                return encode_integer(len(self.store))

            if name == "STATS":
                if args:
                    return encode_error("STATS takes no arguments")

                stats = self.store.stats()
                return encode_simple_string(str(stats))

            return encode_error(f"unknown command '{name}'")

        except (ValueError, TypeError) as exc:
            return encode_error(str(exc))


if __name__ == "__main__":
    server = TCPServer()
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.stop()