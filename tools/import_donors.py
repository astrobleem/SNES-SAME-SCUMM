#!/usr/bin/env python3
from same.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["donors", "import", *__import__("sys").argv[1:]]))
