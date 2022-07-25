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
        self._matching_data: dict[str, dict[str, tuple[str, int | None]]] = {}
        # self.matching_headers = {}
        self._initialize_responses_dict()
        self._initialize_matching_data()

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
                matching_data = self._get_functions_and_fields_matching_request_body(
                    request_body
                )
                if matching_data:
                    self._matching_data[current_function] = matching_data

    def _get_functions_and_fields_matching_request_body(
        self, request_body: dict[str, str]
    ) -> dict[str, tuple[str, int | None]]:
        matching_functions_and_fields = {}
        list_of_matching_data = []

        for request_body_item in request_body.items():
            field_name, value = request_body_item

            function_name = self._get_function_producing_this_value(value)
            if function_name:
                matching_data = (field_name, self._get_data_matching_value(value))

                if matching_data:
                    list_of_matching_data.append(matching_data)

                if len(list_of_matching_data) > 1:
                    matching_functions_and_fields[function_name] = list_of_matching_data
                else:
                    matching_functions_and_fields[
                        function_name
                    ] = list_of_matching_data[0]
        return matching_functions_and_fields

    def _get_function_producing_this_value(self, value: str) -> str | None:
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

    def _get_data_matching_value(self, value: str) -> tuple[str, int | None] | None:
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

    # def init_first_response(self):
    #     for requestify_object in self.requests:
    #         response = get_response(requestify_object)
    #
    #         if is_valid_response(response):
    #             self.map_response_to_current_function(
    #                 requestify_object.function_name, response
    #             )
    #
    # def add_new_request(self, requestify_object):
    #     response = get_response(requestify_object)
    #
    #     if is_valid_response(response):
    #         self.map_response_to_current_function(
    #             requestify_object.function_name, response
    #         )


#
#     @staticmethod
#     def get_response_field_name_and_index(sought_value, list_of_dicts):
#         for index, dict in enumerate(list_of_dicts):
#             ret = ReplaceRequestify.get_field_name_matching_value(sought_value, dict)
#             if ret:
#                 return (ret, index)
#
#     @staticmethod
#     def get_field_name_matching_value(sought_value, dict):
#         for field_name, value in dict.items():
#             if sought_value == value:
#                 return field_name
#
#     @staticmethod
#     def add_index_if_needed(data_string, index):
#         data_string_with_index = ""
#         if index is not None:
#             data_string_with_index = data_string + f"[{index}],"
#         else:
#             data_string_with_index = data_string + ","
#
#         return data_string_with_index
#
#     def format_data_line(self, matching_data):
#         data_string_with_index = ""
#         data_parts = [f"data={{"]
#
#         for function_called, list_of_fields in matching_data.items():
#             for request_field, (response_field, index) in list_of_fields:
#                 data_part = f"'{request_field}': {RESPONSES_DICT_NAME}['{function_called}']['{response_field}']"
#                 data_string_with_index = ReplaceRequestify.add_index_if_needed(
#                     data_part, index
#                 )
#
#                 data_parts.append(data_string_with_index)
#
#         data_string_with_index += "}"
#         return "\n".join(data_parts)
#
#     @staticmethod
#     def replace_response_data(response_as_list, formatted_data_line, has_data=False):
#         response_with_replaced_data = response_as_list
#
#         if has_data:
#             response_with_replaced_data[2] = formatted_data_line
#
#         return response_with_replaced_data
#
#     @staticmethod
#     def replace_response_containing_data(response_as_list, formatted_data_line):
#         return ReplaceRequestify.replace_response_data(
#             response_as_list, formatted_data_line, has_data=True
#         )
#
#     @staticmethod
#     def replace_response_not_containing_data(response_as_list, formatted_data_line):
#         return ReplaceRequestify.replace_response_data(
#             response_as_list, formatted_data_line, has_data=True
#         )
#
#     def get_formatted_response(self, request):
#         base_response = super().create_base_response(request=request)
#         matching_data = self.matching_data.get(request.function_name)
#
#         data_line = self.format_data_line(matching_data=matching_data)
#         base_response[2] = data_line
#
#         if request.data:
#             formatted_response = ReplaceRequestify.replace_response_containing_data(
#                 base_response, data_line
#             )
#         else:
#             formatted_response = ReplaceRequestify.replace_response_not_containing_data(
#                 base_response, data_line
#             )
#
#         pprint(formatted_response)
#
#     def get_replaced_functions(self):
#         base_text = super().__create_base_response()
#
#     def __create_responses_text(self, with_headers=True, with_cookies=True):
#
#         requests_text = [
#             generate_imports_text(["requests", "pprint"]),
#             generate_class(
#                 REQUESTS_CLASS_NAME,
#             ),  # < should be all the functions
#         ]
#
#     def __write_to_stdio(self, with_headers=True, with_cookies=True):
#         requests_as_functions = self.__create_responses_text(
#             with_headers=with_headers, with_cookies=with_cookies
#         )
#         print(requests_as_functions)
#
#     def to_screen(self):
#         self.__write_to_stdio()
#
#
# def __get_file(filename):
#     requests = []
#     request = ""
#     with open(filename, mode="r") as in_file:
#         for line in in_file:
#             request += line
#             if "curl" in line:
#                 requests.append(request)
#                 request = ""
#     return requests
#
#
# def from_file(filename, replace=False):
#     requests_from_file = __get_file(filename)
#     assert requests_from_file, "No data in the specified file"
#
#     if len(requests_from_file) == 1:
#         requests = RequestifyObject(requests_from_file[0])
#     else:
#         if replace:
#             requests = ReplaceRequestify(requests_from_file)
#         else:
#             requests = RequestifyList(requests_from_file)
#     return requests
