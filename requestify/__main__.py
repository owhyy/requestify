import argparse
import sys
import requestify


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
        help="Use clipboard and write to stdout",
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
        requestify.from_string(args.s).to_screen()

    if args.f:
        requestify.from_file(args.f).to_screen()

    if args.c and args.s:
        requestify.from_string(args.s).to_clipboard()

    if args.c and args.f:
        requestify.from_file(args.f).to_clipboard()

    if args.s and args.o:
        requestify.from_string(args.s).to_file(args.o)

    if args.f and args.o:
        requestify.from_file(args.s).to_file(args.o)


def main():
    parser = get_args()
    parse_args(parser)


if __name__ == "__main__":
    main()
