# !/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
import sys
import argparse
import pyperclip
import json
from collections import defaultdict
from urllib import parse, request
from black import format_str, FileMode

# name that will be used for class with requests
REQUESTS_CLASS_NAME = "RequestsTest"


def get_data_dict(query):
    _ = dict(parse.parse_qsl(query))
    return _ if len(_) > 0 else query


class RequestifyObject(object):
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

    # returns base(without imports, only the text), unbeautified string
    def create_responses_base(self, indent="", with_headers=True, with_cookies=True):
        request_options = ""
        wait_to_write = []
        if with_headers:
            wait_to_write.append(f"{indent}headers = {self.headers}")
            request_options += ", headers=headers"

        if with_cookies:
            wait_to_write.append(f"{indent}cookies = {self.cookies}")
            request_options += ", cookies=cookies"

        if self.method == "post":
            wait_to_write.append(f"{indent}data = {self.data}")
            request_options += ", data=data"

        wait_to_write.append(
            f"{indent}response = requests.{self.method}('{self.url}'"
            + request_options
            + ")"
        )

        wait_to_write.append(f"{indent}print(response.text)")
        return f"\n".join(wait_to_write)

    # returns beautified string
    def __create_responses_string(self, with_headers=True, with_cookies=True):
        request_options = ""
        response = self.create_responses_base("", with_headers, with_cookies)
        wait_to_write = [
            "import requests",
            "\n",
            response,
            "\n\n",
        ]

        return self.__beautify_string("".join(wait_to_write))

    @staticmethod
    def __beautify_string(response):
        return format_str(response, mode=FileMode())

    def __write_to_file(self, file, with_headers=True, with_cookies=True):
        request = self.__create_responses_string(with_headers, with_cookies)
        with open(file, "w") as f:
            f.write("\n".join(request) + "\n")

    def __write_to_stdio(self, with_headers=True, with_cookies=True):
        request = self.__create_responses_string(with_headers, with_cookies)
        print(request)


class __GenerateList(object):
    def __init__(self, base_list):
        self.base_list = base_list
        self.requests = []
        self.existing_function_names = defaultdict(int)
        self.__generate()

    def __generate(self):
        for curl in self.base_list:
            request = RequestifyObject(curl)
            self.requests.append(request)

    def __create_responses_text(self):
        requests_text = [
            "import requests",
            "\n\n",
            f"class {REQUESTS_CLASS_NAME}():",
            "\n",
        ]
        function_names = []
        for request in self.requests:
            function_name = self.__create_function_name(request)
            function_names.append(function_name)

            response = request.create_responses_base(indent="\t\t")
            requests_text.append(f"\tdef {function_name}(self):{response}")
            requests_text.append("\n")

        requests_text.append("\n\t")
        requests_text.append("def call_all(self):")
        requests_text.append("\n\t\t")
        requests_text.append(
            "\n\t\t".join(
                [f"self.{function_name}()" for function_name in function_names]
            )
        )

        requests_text.append("\n\n")
        requests_text.append("if __name__ == '__main__': ")
        requests_text.append("\n\t")
        requests_text.append(f"{REQUESTS_CLASS_NAME}().call_all()")
        # return "".join(requests_text)
        return format_str("".join(requests_text), mode=FileMode())

    # TODO: test this
    def __create_function_name(self, request):
        _ = request.url.split("/")
        url = _[2] if len(_) > 2 else _[0]
        url = url.replace(".", "_")

        function_name = f"{url}_{request.method}"

        function_count = self.existing_function_names[function_name]

        ret = f"{function_name}{'_' + str(function_count) if function_count else ''}"

        self.existing_function_names[function_name] += 1
        return ret

    def to_file(self, filename):
        self.__write_to_file(filename)

    def to_screen(self):
        self.__write_to_stdio()

    def __write_to_file(self, file):
        requests_as_functions = self.__create_responses_text()

        with open(file, "w") as f:
            f.write("\n".join(requests_as_functions) + "\n")

    def __write_to_stdio(self, with_headers=True, with_cookies=True):
        requests_as_functions = self.__create_responses_text()
        print(requests_as_functions)


def __get_file(filename):
    requests = []
    with open(filename, mode="r") as in_file:
        for line in in_file:
            requests.append(line)
    return requests


def __get_clipboard():
    return pyperclip.paste()


def from_string(base_string):
    return RequestifyObject(base_string)


def from_clipboard():
    return RequestifyObject(__get_clipboard())


def from_file(filename):
    requests_from_file = __get_file(filename)
    assert requests_from_file, "No data in the specified file"
    if len(requests_from_file) == 1:
        requests = RequestifyObject(requests_from_file[0])
    else:
        requests = __GenerateList(requests_from_file)
    return requests


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
    # print(len(__get_file("curls")))
