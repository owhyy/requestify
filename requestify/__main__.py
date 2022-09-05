import sys
import argparse
import pyperclip
from requestify.models import (
    _RequestifyList,
    _RequestifyObject,
    _ReplaceRequestify,
)


def _get_file(filename: str) -> list[str]:
    requests = []
    request = ''
    with open(filename, mode='r', encoding='utf8') as in_file:
        for line in in_file:
            request += line
            if 'curl' in line:
                requests.append(request)
                request = ''
    return requests


def from_string(base_string):
    return _RequestifyObject(base_string)


def from_clipboard():
    return _RequestifyObject(pyperclip.paste())


def from_file(filename, replace=False):
    requests_from_file = _get_file(filename)
    assert requests_from_file, 'No data in the specified file'
    if len(requests_from_file) == 1:
        assert (
            not replace
        ), 'No requests to replace (only one request was passed)'
        requests = _RequestifyObject(requests_from_file[0])
    else:
        if replace:
            requests = _ReplaceRequestify(*requests_from_file)
        else:
            requests = _RequestifyList(*requests_from_file)
    return requests


def get_args():
    arg = argparse.ArgumentParser(description='Convert cURL to requests.')

    arg.add_argument(
        '-s',
        metavar='string',
        type=str,
        help='Use cURL from string',
    )

    arg.add_argument(
        '-f',
        metavar='file',
        help='Use cURLs from file',
    )

    arg.add_argument(
        '-c',
        action='store_true',
        help='Use cURL request from clipboard',
    )

    arg.add_argument('-o', metavar='file', help='Write output to file')

    arg.add_argument('-har', metavar='file', help='Use cURLS from HAR file')
    return arg


def parse_args(parser):
    args = parser.parse_args()

    if len(sys.argv) <= 1:
        parser.print_help()
        sys.exit(1)

    if args.s:
        from_string(args.s)

    if args.f:
        from_file(args.f)

    if args.c and args.s:
        from_clipboard()

    if args.c and args.f:
        from_clipboard()

    if args.s and args.o:
        from_string(args.s)

    if args.f and args.o:
        from_file(args.s)


if __name__ == '__main__':
    parser = get_args()
    parse_args(parser)
