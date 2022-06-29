# !/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
import sys
import argparse
import pyperclip
import json
from urllib import parse, request
from black import format_str, FileMode


def get_data_dict(query):
    _ = dict(parse.parse_qsl(query))
    return _ if len(_) > 0 else query


class __Generate(object):
    def __init__(self, base_string):
        self.base_string = base_string.strip()
        self.url = ""
        self.method = "get"
        self.headers = {}
        self.cookies = {}
        self.querys = {}
        self.data = None
        self.__post_handler = {
            "-d": lambda x: get_data_dict(x),
            "--data": lambda x: get_data_dict(x),
            "--data-ascii": lambda x: get_data_dict(x),
            "--data-binary": lambda x: bytes(x, encoding="utf-8"),
            "--data-raw": lambda x: get_data_dict(x),
            "--data-urlencode": lambda x: parse.quote(x),
        }
        self.__opt_list = []
        self.__generate()
        # self.__key_max_length = 0

    def to_file(self, filename, with_headers=True, with_cookies=True):
        self.__write_to_file(
            filename, with_headers=with_headers, with_cookies=with_cookies
        )

    # def to_current_file(self, with_headers=True, with_cookies=True):
    #     current_filename = sys.argv[0].split("/")[-1]
    #     self.__write_to_file(
    #         current_filename, with_headers=with_headers, with_cookies=with_cookies
    #     )

    def to_screen(self, with_headers=True, with_cookies=True):
        self.__write_to_stdio(with_headers, with_cookies)

    def __generate(self):

        meta = self.base_string.split(" ", 2)
        assert len(meta) == 3, "Not a valid cURL request"
        prefix, url, opts_string = meta
        assert prefix == "curl", "Not a valid cURL request"
        self.url = url[1:-1]

        opts = re.findall(" (-{1,2}\S+) ?\$?'([\S\s]+?)'", opts_string)

        self.__set_opts(opts)

    def __set_opts(self, opts):
        headers = []
        for k, v in opts:
            if k == "-H":
                headers.append(v)
            elif k in self.__post_handler:
                self.method = "post"
                self.data = self.__post_handler[k](v)

        self.__format_headers(headers)

    def __format_cookies(self, text):
        cookies = text.split("; ")
        for cookie in cookies:
            try:
                k, v = cookie.split("=", 1)
                self.cookies[k] = v
            except ValueError:
                raise
                # self.__update_length(k)
        return self.cookies

    def __format_headers(self, headers):
        for header in headers:
            try:
                k, v = header.split(": ", 1)
            except ValueError:
                print(f"invalid data: {header}")
                pass
                # raise

            if k.lower() == "cookie":
                self.__format_cookies(v)
            else:
                self.headers[k] = v
                # self.__update_length(k)
        return self.headers

    def __create_response(self, with_headers=True, with_cookies=True):
        request_options = ""
        wait_to_write = ["import requests", "\n"]

        if with_headers:
            wait_to_write.append(f"headers = {self.headers}\n")
            request_options += ", headers=headers"

        if with_cookies:
            wait_to_write.append(f"cookies = {self.cookies}\n")
            request_options += ", cookies=cookies"

        if self.method == "post":
            # if type(self.data) == dict:
            #     cute_data = self.__beautify(self.data, space=8)
            # else:
            wait_to_write.append(f"data = {self.data}\n")
            request_options += ", data=data"

        wait_to_write.append(
            f"response = requests.{self.method}('{self.url}'" + request_options + ")"
        )
        wait_to_write.append("\nprint(response.text)")
        return self.__beautify_response("".join(wait_to_write))
        # return self.__beautify_response(wait_to_write)

    @staticmethod
    def __beautify_response(response):
        s = "".join(x for x in response)
        return format_str(s, mode=FileMode())

    def __write_to_file(self, file, with_headers=True, with_cookies=True):
        request = self.__create_response(with_headers, with_cookies)
        with open(file, "w") as f:
            f.write("\n".join(request) + "\n")

    def __write_to_stdio(self, with_headers=True, with_cookies=True):
        request = self.__create_response(with_headers, with_cookies)
        print(request)


def __get_file(filename):
    requests = []
    curl = ""
    with open(filename, mode="r") as in_file:
        for line in in_file:
            curl += line
        return curl


def __get_clipboard():
    return pyperclip.paste()


def from_string(base_string):
    return __Generate(base_string)


def from_clipboard():
    print(__get_clipboard())
    return __Generate(__get_clipboard())


def from_file(filename):
    return __Generate(__get_file(filename))


flags_and_messages = {
    "-h, --help": "Get help for commands",
    "-c, --clipboard": "Use clipboard and write to stdout",
    "-f [path], --file [path]": "Use cURLs from file",
    "-o [path], --output [path]": "Write output to file",
}


class WriteToSTDOUT(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        from_string(values).to_screen()


class ClipboardWriteToSTDOUT(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        from_clipboard().to_screen()


class ReadFromFileWriteToSTDOUT(argparse.Action):
    def __call__(self, parser, namespace, filename, option_string=None):
        from_file(filename).to_screen()


def main():
    parser = argparse.ArgumentParser(description="Convert cURL to requests.")
    parser.add_argument(
        "-s",
        "--string",
        nargs="?",
        action=WriteToSTDOUT,
        help="Use string and write to stdout",
    )
    parser.add_argument(
        "-c",
        "--clipboard",
        nargs=0,
        action=ClipboardWriteToSTDOUT,
        help="Use clipboard and write to stdout",
    )
    parser.add_argument(
        "-f",
        "--file",
        nargs="?",
        action=ReadFromFileWriteToSTDOUT,
        help="Use cURLs from file",
    )
    # parser.add_argument(
    #     "-o", "--output", action=PrintStringToScreen, help="Write output to file"
    # )
    return parser.parse_args()


if __name__ == "__main__":
    main()
