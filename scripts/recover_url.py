"""Run with .venv/bin/python -m scripts.recover_url 'https://example.org/'."""

import argparse
from dataclasses import asdict
import json

from relink.network import UnsafeURLError
from relink.recovery import recover_url


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Find an Internet Archive capture of a public URL.')
    parser.add_argument('url', help='Public HTTP(S) URL; standard ports only.')
    args = parser.parse_args(argv)
    try:
        result = recover_url(args.url)
    except UnsafeURLError as exc:
        print(json.dumps({'error': 'unsafe_url', 'detail': str(exc)}, indent=2))
        return 2
    print(json.dumps(asdict(result), indent=2))
    if result.archive.status in ('found', 'not_found'):
        return 0
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
