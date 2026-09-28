# DistriCache

A lightweight, Redis-inspired in-memory key-value store built in Python.

DistriCache provides a thread-safe storage engine with LRU caching, TTL expiration, persistence, replication, a TCP protocol, a REST API, and a command-line client.

## Features

- In-memory key-value storage
- LRU eviction
- TTL-based key expiration
- Thread-safe operations
- AOF persistence support
- Replication support
- Custom TCP server
- RESP-style command protocol
- REST API
- Command-line client
- Automated test suite

## Project Structure

```text
DistriCache/
├── core/
│   ├── consistent_hash.py
│   ├── hash_table.py
│   ├── lru_cache.py
│   └── store.py
├── persistence/
│   └── aof.py
├── replication/
│   └── replicator.py
├── server/
│   ├── protocol.py
│   ├── tcp_server.py
│   └── rest_api.py
├── client/
│   └── cli.py
├── tests/
│   ├── test_consistent_hash.py
│   ├── test_hash_table.py
│   ├── test_lru_cache.py
│   ├── test_store.py
│   ├── test_tcp_server.py
│   └── test_rest_api.py
├── requirements.txt
└── README.md