import argparse
import pyperclip
import sys
from requestify.models import RequestifyList, RequestifyObject
from replace import ReplaceRequestify
import replace


def __get_file(filename):
    requests = []
    request = ""
    with open(filename, mode="r") as in_file:
        for line in in_file:
            request += line
            if "curl" in line:
                requests.append(request)
                request = ""
    return requests


def from_string(base_string):
    return RequestifyObject(base_string)


def from_clipboard():
    return RequestifyObject(pyperclip.paste())


def from_file(filename, replace=False):
    requests_from_file = __get_file(filename)
    assert requests_from_file, "No data in the specified file"
    if len(requests_from_file) == 1:
        requests = RequestifyObject(requests_from_file[0])
    else:
        if replace:
            requests = ReplaceRequestify(requests_from_file)
        else:
            requests = RequestifyList(requests_from_file)
    return requests


def get_args():
    arg = argparse.ArgumentParser(description="Convert cURL to requests.")

    arg.add_argument(
        "-s",
        metavar="string",
        type=str,
        help="Use string and write to stdout",
    )

    arg.add_argument(
        "-c",
        action="store_true",
        help="Use cURL request from clipboard",
    )

    arg.add_argument(
        "-f",
        metavar="file",
        help="Use cURLs from file",
    )

    arg.add_argument("-o", metavar="file", help="Write output to file")

    return arg


def parse_args(parser):
    args = parser.parse_args()

    if len(sys.argv) <= 1:
        parser.print_help()
        sys.exit(1)

    if args.s:
        from_string(args.s).to_screen()

    if args.f:
        from_file(args.f).to_screen()

    if args.c and args.s:
        from_clipboard().to_screen()

    if args.c and args.f:
        from_clipboard().to_file(args.f)

    if args.s and args.o:
        from_string(args.s).to_file(args.o)

    if args.f and args.o:
        from_file(args.s).to_file(args.o)


def main():
    parser = get_args()
    parse_args(parser)


if __name__ == "__main__":
    # main()
    # import cProfile
    # import pstats
    # with cProfile.Profile() as pr:
    # replace.from_file('../tests/test_files/test_data.txt').generate_workflow()
    # replace.from_file('../tests/test_files/test_data.txt').generate_workflow_async()
    from_file("../tests/test_files/test_data.txt", replace=True).debug()

    # stats = pstats.Stats(pr)
    # stats.sort_stats(pstats.SortKey.TIME)
    # stats.print_stats()
