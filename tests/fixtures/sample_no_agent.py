"""Non-agent Python file — should produce no scan results."""
import os
import json
import hashlib
from pathlib import Path
from typing import List, Optional


def read_config(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def compute_hash(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


class DataProcessor:
    def __init__(self, config: dict):
        self.config = config

    def process(self, items: List[str]) -> List[str]:
        return [item.strip().lower() for item in items]


def main():
    config = read_config("config.json")
    processor = DataProcessor(config)
    results = processor.process(["Hello", "World"])
    print(results)


if __name__ == "__main__":
    main()
