# !/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import requests
import itertools
from urllib import parse
from collections import defaultdict
from .utils import get_data_dict, get_netloc, beautify_string, get_json_or_text


# name that will be used for class with requests
REQUESTS_CLASS_NAME = "RequestsTest"
RESPONSE_VARIABLE_NAME = "response"
REQUEST_VARIABLE_NAME = "request"

# methods to be called if data flags are present
DATA_HANDLER = {
    "-d": lambda x: get_data_dict(x),
    "--data": lambda x: get_data_dict(x),
    "--data-ascii": lambda x: get_data_dict(x),
    "--data-binary": lambda x: bytes(x, encoding="utf-8"),
    "--data-raw": lambda x: get_data_dict(x),
    "--data-urlencode": lambda x: parse.quote(x),
}

METHOD_REGEX = re.compile(
    f'({"|".join(name for name in DATA_HANDLER)})|(?:-X)\s+(\S\w+\S)'
)
OPTS_REGEX = re.compile(
    """ (-{1,2}\S+)\s+?"([\S\s]+?)"|(-{1,2}\S+)\s+?'([\S\s]+?)'""", re.VERBOSE
)
URL_REGEX = re.compile(
    "((?:(?<=[^a-zA-Z0-9]){0,}(?:(?:https?\:\/\/){0,1}(?:[a-zA-Z0-9\%]{1,}\:[a-zA-Z0-9\%]{1,}[@]){,1})(?:(?:\w{1,}\.{1}){1,5}(?:(?:[a-zA-Z]){1,})|(?:[a-zA-Z]{1,}\/[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\:[0-9]{1,4}){1})){1}(?:(?:(?:\/{0,1}(?:[a-zA-Z0-9\-\_\=\-]){1,})*)(?:[?][a-zA-Z0-9\=\%\&\_\-]{1,}){0,1})(?:\.(?:[a-zA-Z0-9]){0,}){0,1})"
)


def format_url(url):
    url = url.strip("'").strip('"').rstrip("/")
    if not (
        url.startswith("//") or url.startswith("http://") or url.startswith("https://")
    ):
        url = "https://" + url  # good enough

    return url


def find_url_or_error(s: str) -> str:
    might_include_url = re.search(URL_REGEX, s)
    if might_include_url:
        url = might_include_url.groups(0)[0]
    else:
        raise ValueError("Could not find a url")
    return url  # type: ignore


def get_list_of_strings_without_url(list_of_strings, url):
    return [s for s in list_of_strings if s != url]


# https://stackoverflow.com/questions/5389507/iterating-over-every-two-elements-in-a-list
def pairwise(iterable):
    "s -> (s0, s1), (s2, s3), (s4, s5), ..."
    a = iter(iterable)
    return zip(a, a)


# prolly not working
def uppercase_boolean_values(opts):
    ret_opts = []
    for _, value in opts:
        if value.find("false") != -1:
            value = value.replace("false", "False")
        if value.find("true") != -1:
            value = value.replace("true", "True")
        ret_opts.append((_, value))

    return ret_opts


def find_and_get_opts(meta: str) -> list[str]:
    opts = re.findall(OPTS_REGEX, meta)
    _ = list(itertools.chain.from_iterable(opts))
    return [option for option in _ if option]


def split_and_flatten_list(l):
    return list(itertools.chain.from_iterable([element.split(" ") for element in l]))


class RequestifyObject(object):
    def __repr__(self):
        return f"RequestifyObject({self.base_string})"

    def __init__(self, base_string):
        self.base_string = " ".join(base_string.replace("\\", "").split())
        self.url = ""
        self.method = "get"
        self.headers = {}
        self.cookies = {}
        self.data = dict()

        self.function_name = ""
        self.__generate()

    def __generate(self):
        meta = self.base_string.split(" ", 2)
        assert len(meta) > 1, "No URL provided"
        assert meta[0] == "curl", "Not a valid cURL request"

        if len(meta) == 2:
            url = meta[1]
            self.__initialize_curl_and_url_only(url)
        else:
            self.__initialize_complete_request(" ".join(meta[1:]))

        self.__set_function_name()

    def __initialize_curl_and_url_only(self, url: str) -> None:
        if re.search(URL_REGEX, url):
            self.url = url
            self.method = "get"
        else:
            raise ValueError("Request method not specified, and is not a GET")

    def __initialize_complete_request(self, meta: str) -> None:
        self.__set_url(meta)
        self.__set_method(meta)
        self.__set_opts(meta)

    def __set_url(self, meta: str) -> None:
        self.url = format_url(find_url_or_error(meta))

    def __set_method(self, meta: str) -> None:
        found = re.search(METHOD_REGEX, meta)
        if found:
            dataflag = found.groups()[0]
            method = found.groups()[1]

            if dataflag:
                if self.method == "get":
                    self.method = "post"
            elif method:
                self.method = method.strip("'").strip('"').lower()
        else:
            pass
            # raise

    def __set_opts(self, meta: str) -> None:
        opts = self.__get_opts(meta)
        opts = uppercase_boolean_values(opts)

        self.__set_body(opts)
        headers = [option[1] for option in opts if option[0] == "-H"]
        self.__format_headers(headers)

    # requests does not have support for flags such as --compressed, --resolve,
    # so there's no way to convert
    def __get_opts(self, meta: str) -> list[str]:
        opts = find_and_get_opts(meta)

        assert len(opts) % 2 == 0, "Request header(s) or flag(s) missing"
        ret_opts = []
        for flag, data in pairwise(opts):
            if flag == "-H" or flag in DATA_HANDLER:
                ret_opts.append((flag, data))

        return ret_opts

    def __set_body(self, opts: list[tuple[str]]):
        for option in opts:
            for flag, value in pairwise(option):
                if flag in DATA_HANDLER:
                    self.data = DATA_HANDLER[flag](value)

    def __format_headers(self, headers):
        for header in headers:
            try:
                k, v = header.split(": ", 1)
            except ValueError:
                print(f"invalid data: {header}")
                raise

            if k.lower() == "cookie":
                self.__format_cookies(v)
            else:
                self.headers[k] = v
        return self.headers

    def __format_cookies(self, text):
        cookies = text.split("; ")
        for cookie in cookies:
            try:
                k, v = cookie.split("=", 1)
                self.cookies[k] = v
            except ValueError:
                raise
        return self.cookies

    def __set_function_name(self):
        netloc = get_netloc(self.url)
        function_name = f"{self.method}_{netloc}"
        self.function_name = function_name

    def create_responses_base(self, with_headers=True, with_cookies=True):
        request_options = ""
        wait_to_write = []
        if with_headers:
            wait_to_write.append(f"headers = {self.headers}")
            request_options += ", headers=headers"

        if with_cookies:
            wait_to_write.append(f"cookies = {self.cookies}")
            request_options += ", cookies=cookies"

        if self.data:
            wait_to_write.append(f"data = {self.data}")
            request_options += ", data=data"

        wait_to_write.append(
            f"{REQUEST_VARIABLE_NAME} = requests.{self.method}('{self.url}'{request_options})"
        )

        return wait_to_write

    def create_beautiful_response(self, with_headers=True, with_cookies=True):
        response = "\n".join(self.create_responses_base(with_headers, with_cookies))
        wait_to_write = [
            "import requests",
            response,
        ]

        return beautify_string("\n".join(wait_to_write))

    def __write_to_file(self, file, with_headers=True, with_cookies=True):
        request = self.create_beautiful_response(with_headers, with_cookies)
        with open(file, "w") as f:
            f.write("\n".join(request) + "\n")

    def __write_to_stdio(self, with_headers=True, with_cookies=True):
        request = self.create_beautiful_response(with_headers, with_cookies)
        print(request)

    def to_file(self, filename, with_headers=True, with_cookies=True):
        self.__write_to_file(
            filename, with_headers=with_headers, with_cookies=with_cookies
        )

    def to_screen(self, with_headers=True, with_cookies=True):
        self.__write_to_stdio(with_headers, with_cookies)

    def execute(self):
        request = requests.request(
            method=self.method, url=self.url, headers=self.headers, cookies=self.cookies
        )

        return get_json_or_text(request)


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

        self.__set_function_names()

    def __create_responses_text(self, with_headers=True, with_cookies=True):
        requests_text = [
            "import requests",
            f"class {REQUESTS_CLASS_NAME}:",
        ]

        for request in self.requests:
            response = "\n".join(
                request.create_responses_base(
                    with_headers=with_headers, with_cookies=with_cookies
                )
            )
            requests_text.append(f"def {request.function_name}(self):{response}")

        requests_text.append("def call_all(self):")
        requests_text.append(
            "".join(
                [
                    f"self.{function_name}()\n"
                    for function_name in self.existing_function_names
                ]
            )
        )

        requests_text.append("if __name__ == '__main__': ")
        requests_text.append(f"{REQUESTS_CLASS_NAME}().call_all()")

        return beautify_string("\n".join(requests_text))

    def __set_function_names(self):
        for request in self.requests:
            function_count = self.existing_function_names[request.function_name]
            function_name = f"{request.function_name}{('_' + str(function_count) if function_count else '')}"
            request.function_name = (
                function_name if function_name else request.function_name
            )
            self.existing_function_names[function_name] += 1

    def __write_to_file(self, file):
        requests_as_functions = self.__create_responses_text()

        with open(file, "w") as f:
            f.write("\n".join(requests_as_functions) + "\n")

    def __write_to_stdio(self, with_headers=True, with_cookies=True):
        requests_as_functions = self.__create_responses_text(with_headers, with_cookies)
        print(requests_as_functions)

    def to_file(self, filename):
        self.__write_to_file(filename)

    def to_screen(self):
        self.__write_to_stdio()
