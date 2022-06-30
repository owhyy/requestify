# !/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import io
import re
import sys
import argparse
import pyperclip
import json
from collections import defaultdict
from urllib import parse, request
from black import format_str, FileMode
from contextlib import redirect_stdout

# name that will be used for class with requests
REQUESTS_CLASS_NAME = "RequestsTest"


def get_data_dict(query):
    data = dict(parse.parse_qsl(query))
    return data if len(data) > 0 else query


class RequestifyObject(object):
    def __init__(self, base_string):
        # self.base_string = base_string.strip().replace("\\", "").replace("\n", "")
        self.base_string = " ".join(base_string.replace("\\", "").split())
        self.url = ""
        self.method = "get"
        self.headers = {}
        self.cookies = {}
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

    def to_file(self, filename, with_headers=True, with_cookies=True):
        self.__write_to_file(
            filename, with_headers=with_headers, with_cookies=with_cookies
        )

    def to_screen(self, with_headers=True, with_cookies=True):
        self.__write_to_stdio(with_headers, with_cookies)

    def __generate(self):
        meta = self.base_string.split(" ", 2)
        opts = {}
        assert len(meta) > 1, "Not a valid cURL request"

        if len(meta) == 2:
            prefix, url = meta
        else:
            # normal order is curl url -X GET
            prefix, url_or_flag, opts_string = meta

            # if request is like curl -X GET url -H headers, flag will be second, not url
            if url_or_flag == "-X":  # TODO: replace with better check (more flags)
                # flag = "-X" maybe we'll need different flags
                method_and_url = opts_string.split(" ", 2)
                assert len(method_and_url) > 1, "Not a valid cURL request"

                method = method_and_url[0].rstrip(":")
                url = method_and_url[1]

                if len(method_and_url) == 3:
                    opts_string = method_and_url[2]
            else:
                # if request is like curl url -X GET -H headers, url will be second, and method with flag 3rd
                url = url_or_flag
                flag_with_method_or_header = opts_string.split(" ", 2)
                assert len(flag_with_method_or_header) > 1, "Not a valid cURL request"

                flag = flag_with_method_or_header[0]
                if flag == "-X":
                    method = flag_with_method_or_header[1].rstrip(":")
                else:
                    opts_string = " " + opts_string
                    method = "get"

            opts = re.findall(" (-{1,2}\S+) ?\$?'([\S\s]+?)'", opts_string)
            self.method = method.strip("'").strip('"').lower()

            self.__set_opts(opts)

        assert prefix.strip("'").strip('"') == "curl", "Not a valid cURL request"
        self.url = url.strip("'").strip('"').rstrip("/")
        # self.url = url.strip("'").strip('"').rstrip("/") + "/"

    def __set_opts(self, opts):
        headers = []
        for k, v in opts:
            if k == "-H":
                headers.append(v)

            # possible_bool = v.split(":")
            if v.find('false') != -1:
                v = v.replace('false', "False")
            elif v.find('true') != -1:
                v = v.replace('true', "Talse")
            # v = ":".join(possible_bool)

            # if len(possible_bool) > 1:
                ## if the value is not a string, it can be a boolean, integer ...
                # if not isinstance(possible_bool[1], str):
                #     possible_bool_as_str = str(v)
                #     if possible_bool_as_str == "false":
                #         v.split[""] = False
                #     elif possible_bool_as_str == "true":
                #         v.split[""] = True


            if k in self.__post_handler and self.method == 'get':
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

            if k.lower() == "cookie":  # type: ignore
                self.__format_cookies(v)  # type: ignore
            else:
                self.headers[k] = v  # type: ignore
                # self.__update_length(k)
        return self.headers

    # returns base(without imports, only the text), unbeautified string
    def create_responses_base(self, indent="", with_headers=True, with_cookies=True):
        request_options = ""
        wait_to_write = [indent]
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
    def create_beautiful_response(self, with_headers=True, with_cookies=True):
        request_options = "\t"
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
        request = self.create_beautiful_response(with_headers, with_cookies)
        with open(file, "w") as f:
            f.write("\n".join(request) + "\n")

    def __write_to_stdio(self, with_headers=True, with_cookies=True):
        request = self.create_beautiful_response(with_headers, with_cookies)
        print(request)

    def execute(self, with_headers=True, with_cookies=True):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exec(self.create_beautiful_response(with_headers, with_cookies))

        return stdout.getvalue()


class RequestifyList(object):
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
        url = re.findall(r"\/+(.*?)\/|\.(.*?)\/", request.url)
        url_regex = re.compile(r"[^0-9a-zA-Z_]+")
        if url:
            # if is //url.com/
            if url[0][0]:
                url = re.sub(url_regex, "_", url[0][0])
            # if is www.url.com/
            else:
                url = re.sub(url_regex, "_", url[0][0])

            function_name = f"{url}_{request.method}"
        else:
            function_name = f"{request.method}"

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

    def execute(self, with_headers=True, with_cookies=True):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exec(self.__create_responses_text())
        return stdout.getvalue()


def __get_file(filename):
    requests = []
    request = ""
    with open(filename, mode="r") as in_file:
        for line in in_file:
            request += line
            if re.findall("--compressed", line):
                requests.append(request)
                request = ""
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
        requests = RequestifyList(requests_from_file)
    return requests


class UseString(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        from_string(values).to_screen()


class UseClipboard(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        from_clipboard().to_screen()


class UseFile(argparse.Action):
    def __call__(self, parser, namespace, filename, option_string=None):
        from_file(filename).to_screen()


class WriteToFile(argparse.Action):
    def __call__(self, parser, namespace, filename, option_string=None):
        from_file(filename).to_file(filename)


def main():
    parser = argparse.ArgumentParser(description="Convert cURL to requests.")
    parser.add_argument(
        "-s",
        "--string",
        nargs="?",
        action=UseString,
        help="Use string and write to stdout",
    )
    parser.add_argument(
        "-c",
        "--clipboard",
        nargs=0,
        action=UseClipboard,
        help="Use clipboard and write to stdout",
    )
    parser.add_argument(
        "-f",
        "--file",
        nargs="?",
        action=UseFile,
        help="Use cURLs from file",
    )
    parser.add_argument(
        "-o", "--output", action=WriteToFile, help="Write output to file"
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
