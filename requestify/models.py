# !/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from typing import Any
import requests
from collections import defaultdict
from requestify import utils


RESPONSES_DICT_NAME = "workflow"
JSON_ERROR_NAME = "JSONDecodeError"


class _RequestifyObject(object):
    def __str__(self):
        return self._function_name

    def __repr__(self):
        return f"RequestifyObject({self._base_string})"

    # used for easier testing
    def __eq__(self, other):
        return (
            self._base_string == other._base_string
            and self._url == other._url
            and self._method == other._method
            and self._cookies == other._cookies
            and self._data == other._data
            and self._function_name == other._function_name
        )

    def __init__(self, base_string: str) -> None:
        self._base_string = " ".join(base_string.replace("\\", "").split())
        self._url = ""
        self._method = "get"
        self._headers = {}
        self._cookies = {}
        self._data: RequestDataType = dict()

        self._function_name = ""
        self._generate()

    def _generate(self) -> None:
        meta = self._base_string.split(" ", 2)
        assert len(meta) > 1, "No URL provided"
        assert meta[0] == "curl", "Not a valid cURL request"

        if len(meta) == 2:
            url = meta[1]
            self._initialize_curl_and_url_only(url)
        else:
            self._initialize_complete_request(" ".join(meta[1:]))

        self._set_function_name()

    def _initialize_curl_and_url_only(self, url: str) -> None:
        if re.search(utils.URL_REGEX, url):
            self._url = url
            self._method = "get"
        else:
            raise ValueError("Request method not specified, and is not a GET")

    def _initialize_complete_request(self, meta: str) -> None:
        self._set_url(meta)
        self._set_method(meta)
        self._set_opts(meta)

    def _set_url(self, meta: str) -> None:
        self._url = utils.format_url(utils.find_url_or_error(meta))

    def _set_method(self, meta: str) -> None:
        found = utils.find_method(meta)
        if found:
            dataflag, method = found.groups()

            if dataflag:
                if self._method == "get":
                    self._method = "post"
            elif method:
                self._method = method.strip("'").strip('"').lower()
        else:
            pass
            # raise

    def _set_opts(self, meta: str) -> None:
        opts = self._get_opts(meta)
        opts = utils.uppercase_boolean_values(opts)
        self._set_body(opts)

        headers = [option[1] for option in opts if option[0] == "-H"]
        self._set_headers(headers)

    # requests does not have support for flags such as --compressed, --resolve,
    # so there's no way to convert
    def _get_opts(self, meta: str) -> list[tuple[str, str]]:
        opts = utils.find_and_get_opts(meta)
        assert len(opts) % 2 == 0, "Request header(s) or flag(s) missing"
        return [
            (flag, data)
            for flag, data in utils.pairwise(opts)
            if flag == "-H" or flag in utils.DATA_HANDLER
        ]

    def _set_body(self, opts: list[tuple[str, str]]) -> None:
        for option in opts:
            for flag, value in utils.pairwise(option):
                if flag in utils.DATA_HANDLER:
                    self._data = utils.DATA_HANDLER[flag](value)

    def _set_headers(self, headers: list[str]) -> None:
        for header in headers:
            try:
                k, v = header.split(": ", 1)
            except ValueError:
                print(f"invalid data: {header}")
                raise

            if k.lower() == "cookie":
                self._set_cookie(v)
            else:
                self._headers[k] = v

    def _set_cookie(self, text: str) -> None:
        cookies = text.split("; ")
        for cookie in cookies:
            try:
                k, v = cookie.split("=", 1)
                self._cookies[k] = v
            except ValueError:
                raise

    def _set_function_name(self) -> None:
        netloc = utils.get_netloc(self._url)
        function_name = f"{self._method}_{netloc}"
        self._function_name = function_name

    # def __write_to_file(self, file, with_headers=True, with_cookies=True):
    #     request = self.create_beautiful_response(with_headers, with_cookies)
    #     with open(file, "w") as f:
    #         f.write("\n".join(request) + "\n")
    #
    # def __write_to_stdio(self, with_headers=True, with_cookies=True):
    #     request = self.create_beautiful_response(with_headers, with_cookies)
    #     print(request)
    #
    # def to_file(self, filename, with_headers=True, with_cookies=True):
    #     self.__write_to_file(
    #         filename, with_headers=with_headers, with_cookies=with_cookies
    #     )
    #
    # def to_screen(self, with_headers=True, with_cookies=True):
    #     self.__write_to_stdio(with_headers, with_cookies)
    #
    # def execute(self):
    #     request = requests.request(
    #         method=self.method, url=self.url, headers=self.headers, cookies=self.cookies
    #     )
    #
    #     return utils.get_json_or_text(request)
    #


class _RequestifyList(object):
    def __init__(self, *curls: str):
        self._base_list = curls
        self._requests: list[_RequestifyObject] = []
        self._existing_function_names = defaultdict(int)
        self._generate()

    def __str__(self):
        return f"RequestifyList{[request.__str__() for request in self._requests]}"

    def __repr__(self):
        return f"RequestifyList{[request.__repr__() for request in self._requests]}"

    def _generate(self) -> None:
        for curl in self._base_list:
            request = _RequestifyObject(curl)
            self._requests.append(request)

        self._set_function_names()

    def _set_function_names(self) -> None:
        for request in self._requests:
            base_function_name = request._function_name
            function_count = self._existing_function_names[base_function_name]
            function_name = f"{base_function_name}{('_' + str(function_count) if function_count else '')}"
            request._function_name = (
                function_name if function_name else base_function_name
            )
            self._existing_function_names[base_function_name] += 1


RequestDataType = dict[str, Any]
ResponseDataType = str | RequestDataType | list[RequestDataType]


class _ReplaceRequestify(_RequestifyList):
    def __init__(self, *curls):
        super().__init__(*curls)

        # the name of the function data it produced
        self._function_names_and_their_responses: dict[str, ResponseDataType] = {}
        self._matching_data: dict[tuple[str, str], tuple[str, str, int | None]] = {}
        # self._matching_headers: dict[str, dict[str, tuple[str, str]]] = {}
        # self._matching_url_content: dict[str, dict[str, tuple[str, str]]] = {}
        self._initialize_responses_dict()
        self._initialize_matching_data()
        # self._initialize_matching_headers()
        # self._initialize_matching_url_values()

    def _initialize_responses_dict(self) -> None:
        assert len(self._requests) > 0, "There must be at least one request"
        responses = utils.get_responses(self._requests)
        for request, response in zip(self._requests, responses):
            self._function_names_and_their_responses[request._function_name] = response

    def _initialize_matching_data(self) -> None:
        for request in self._requests:
            request_body = request._data
            current_function = request._function_name
            if request_body:
                (
                    matching_function,
                    matching_field,
                    current_field,
                    index,
                ) = self._get_matching_data(request_body)

                if matching_function and current_field and matching_field:
                    key = (current_function, current_field)
                    matching_data = (matching_function, matching_field, index)
                    self._matching_data[key] = matching_data

    def _get_matching_data(
        self, request_body: dict[str, str]
    ) -> tuple[str, str, str, int | None] | None:
        matching_data = None

        for request_body_item in request_body.items():
            current_field, value = request_body_item
            matching_function = self._get_function_producing_value(value)
            if matching_function:
                # TODO: test this
                matching_field, index = self._get_matching_field_and_index(value)

                if matching_field:
                    matching_data = (
                        matching_function,
                        matching_field,
                        current_field,
                        index,
                    )

        return matching_data

    def _get_function_producing_value(self, value: str) -> str | None:
        for (
            function_name,
            response_data,
        ) in self._function_names_and_their_responses.items():
            if self._is_found_in_data(value, response_data):
                return function_name

    @staticmethod
    def _is_found_in_data(value: str, data: ResponseDataType) -> bool:
        if isinstance(data, dict):
            return value in data.values()
        elif isinstance(data, list):
            for response in data:
                return _ReplaceRequestify._is_found_in_data(value, response)
        else:
            return data == value

        return False

    def _get_matching_field_and_index(
        self, value: str
    ) -> tuple[str, int | None] | None:
        for response in self._function_names_and_their_responses.values():
            # if the response is a list, add index to tuple
            if isinstance(response, list):
                return self._get_field_name_and_index_where_values_match(
                    value, response, True
                )

            else:
                return self._get_field_name_and_index_where_values_match(
                    value, response, False
                )

    @staticmethod
    def _get_field_name_and_index_where_values_match(
        value: str, response: ResponseDataType, has_index=True
    ) -> tuple[str, int | None] | None:
        return_tuple = None
        if isinstance(response, dict):
            for field_name, response_value in response.items():
                if value == response_value:
                    return_tuple = (field_name, None)
        elif isinstance(response, list):
            for index, data_dict in enumerate(response):
                if data_dict:
                    for field_name, response_value in data_dict.items():
                        if value == response_value:
                            if has_index:
                                return_tuple = (field_name, index)
                            else:
                                return_tuple = (field_name, None)

        else:
            return_tuple = None
        return return_tuple
