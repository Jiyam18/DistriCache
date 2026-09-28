"""
Command-line client for DistriCache REST API.
"""

import argparse

import httpx


BASE_URL = "http://127.0.0.1:8000"


def main():
    parser = argparse.ArgumentParser(description="DistriCache CLI")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # GET
    get_parser = subparsers.add_parser("get")
    get_parser.add_argument("key")

    # SET
    set_parser = subparsers.add_parser("set")
    set_parser.add_argument("key")
    set_parser.add_argument("value")

    # DELETE
    delete_parser = subparsers.add_parser("delete")
    delete_parser.add_argument("key")

    # EXISTS
    exists_parser = subparsers.add_parser("exists")
    exists_parser.add_argument("key")

    # KEYS
    subparsers.add_parser("keys")

    # STATS
    subparsers.add_parser("stats")

    args = parser.parse_args()

    if args.command == "get":
        response = httpx.get(f"{BASE_URL}/keys/{args.key}")
    elif args.command == "set":
        response = httpx.put(
            f"{BASE_URL}/keys/{args.key}",
            json={"value": args.value},
        )
    elif args.command == "delete":
        response = httpx.delete(f"{BASE_URL}/keys/{args.key}")
    elif args.command == "exists":
        response = httpx.get(f"{BASE_URL}/keys/{args.key}/exists")
    elif args.command == "keys":
        response = httpx.get(f"{BASE_URL}/keys")
    elif args.command == "stats":
        response = httpx.get(f"{BASE_URL}/stats")
    else:
        return

    print(response.status_code)
    print(response.json())


if __name__ == "__main__":
    main()