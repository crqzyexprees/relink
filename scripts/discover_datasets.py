"""JSON discovery demo: python -m scripts.discover_datasets --title iris."""

import argparse
from dataclasses import asdict
import json

from relink.models import SearchQuery
from relink.recovery import discover_datasets


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Discover research datasets using public metadata.')
    parser.add_argument('--title', default='')
    parser.add_argument('--author', default='')
    parser.add_argument('--institution', default='')
    parser.add_argument('--year', type=int)
    parser.add_argument('--url', default='', help='Original URL; also queries Internet Archive.')
    parser.add_argument('--doi', default='')
    parser.add_argument('--description', default='')
    parser.add_argument('--filename', action='append', default=[])
    parser.add_argument('--version', default='')
    args = parser.parse_args(argv)
    try:
        query = SearchQuery(title=args.title, author=args.author, institution=args.institution,
                            year=args.year, original_url=args.url, doi=args.doi,
                            description=args.description, filenames=tuple(args.filename), version=args.version)
        result = discover_datasets(query)
    except ValueError as exc:
        print(json.dumps({'error': 'invalid_query', 'detail': str(exc)}, indent=2))
        return 2
    print(json.dumps(asdict(result), indent=2))
    return 0 if result.status in ('found', 'not_found') else 1


if __name__ == '__main__':
    raise SystemExit(main())
