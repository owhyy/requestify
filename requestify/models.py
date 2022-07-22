# !/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from typing import Any
import requests
from collections import defaultdict
from requestify import utils


RESPONSES_DICT_NAME = "workflow"
JSON_ERROR_NAME = "JSONDecodeError"

RequestDataType = dict[str, Any]
ResponseDataType = RequestDataType | list[RequestDataType]


class RequestifyObject(object):
    def __str__(self):

        return self.function_name

    def __repr__(self):
        return f"RequestifyObject({self.base_string})"

    # used for easier testing
    def __eq__(self, other):
        return (
            self.base_string == other.base_string
            and self.url == other.url
            and self.method == other.method
            and self.cookies == other.cookies
            and self.data == other.data
            and self.function_name == other.function_name
        )

    def __init__(self, base_string: str) -> None:
        self.base_string = " ".join(base_string.replace("\\", "").split())
        self.url = ""
        self.method = "get"
        self.headers = {}
        self.cookies = {}
        self.data: RequestDataType = dict()

        self.function_name = ""
        self.__generate()

    def __generate(self) -> None:
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
        if re.search(utils.URL_REGEX, url):
            self.url = url
            self.method = "get"
        else:
            raise ValueError("Request method not specified, and is not a GET")

    def __initialize_complete_request(self, meta: str) -> None:
        self.__set_url(meta)
        self.__set_method(meta)
        self.__set_opts(meta)

    def __set_url(self, meta: str) -> None:
        self.url = utils.format_url(utils.find_url_or_error(meta))

    def __set_method(self, meta: str) -> None:
        found = re.search(utils.METHOD_REGEX, meta)
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
        opts = utils.uppercase_boolean_values(opts)
        self.__set_body(opts)

        headers = [option[1] for option in opts if option[0] == "-H"]
        self.__set_headers(headers)

    # requests does not have support for flags such as --compressed, --resolve,
    # so there's no way to convert
    def __get_opts(self, meta: str) -> list[tuple[str, str]]:
        opts = utils.find_and_get_opts(meta)
        assert len(opts) % 2 == 0, "Request header(s) or flag(s) missing"
        return [
            (flag, data)
            for flag, data in utils.pairwise(opts)
            if flag == "-H" or flag in utils.DATA_HANDLER
        ]

    def __set_body(self, opts: list[tuple[str, str]]) -> None:
        for option in opts:
            for flag, value in utils.pairwise(option):
                if flag in utils.DATA_HANDLER:
                    self.data = utils.DATA_HANDLER[flag](value)

    def __set_headers(self, headers: list[str]) -> None:
        for header in headers:
            try:
                k, v = header.split(": ", 1)
            except ValueError:
                print(f"invalid data: {header}")
                raise

            if k.lower() == "cookie":
                self.__set_cookie(v)
            else:
                self.headers[k] = v

    def __set_cookie(self, text: str) -> None:
        cookies = text.split("; ")
        for cookie in cookies:
            try:
                k, v = cookie.split("=", 1)
                self.cookies[k] = v
            except ValueError:
                raise

    def __set_function_name(self) -> None:
        netloc = utils.get_netloc(self.url)
        function_name = f"{self.method}_{netloc}"
        self.function_name = function_name

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


class RequestifyList(object):
    def __init__(self, *curls: str):
        self.base_list = curls
        self.requests: list[RequestifyObject] = []
        self.existing_function_names = defaultdict(int)
        self.__generate()

    def __str__(self):
        return f"RequestifyList{[request.__str__() for request in self.requests]}"

    def __repr__(self):
        return f"RequestifyList{[request.__repr__() for request in self.requests]}"

    def __generate(self) -> None:
        for curl in self.base_list:
            request = RequestifyObject(curl)
            self.requests.append(request)

        self.__set_function_names()

    def __set_function_names(self) -> None:
        for request in self.requests:
            base_function_name = request.function_name
            function_count = self.existing_function_names[base_function_name]
            function_name = f"{base_function_name}{('_' + str(function_count) if function_count else '')}"
            request.function_name = (
                function_name if function_name else base_function_name
            )
            self.existing_function_names[base_function_name] += 1


class ReplaceRequestify(RequestifyList):
    def __init__(self, *curls):
        super().__init__(*curls)

        # the name of the function data it produced
        self.function_names_and_their_responses: dict[str, ResponseDataType] = {}
        self.matching_data = {}
        # self.matching_headers = {}

        self.__generate()

    def __generate(self) -> None:
        # self.init_first_response()
        self.initialize_responses_dict()
        self.initialize_matching_data()

    def initialize_responses_dict(self) -> None:
        assert len(self.requests) > 0, "There must be at least one request"

        responses = utils.get_responses(self.requests)
        self.map_all_functions_to_their_responses(responses)

    def map_all_functions_to_their_responses(self, responses: list[Any]) -> None:
        for request, response in zip(self.requests, responses):
            self.map_response_to_current_function(request.function_name, response)

    def map_response_to_current_function(
        self, function_name: str, response: Any
    ) -> None:
        if not isinstance(response, str):
            self.function_names_and_their_responses[
                function_name
            ] = response

    def initialize_matching_data(self) -> None:
        for request in self.requests:
            request_body = request.data
            current_function = request.function_name
            if request_body:
                matching_data = self.get_functions_and_fields_matching_request_body(
                    request_body
                )
                self.matching_data[current_function] = matching_data

    def get_functions_and_fields_matching_request_body(
        self, request_body: dict[str, str]
    ) -> dict[str, tuple[str, int | None]]:
        matching_functions_and_fields = defaultdict(list)

        for request_body_item in request_body.items():
            # 0 is name of field (content-type, Accept, ...), 1 is value (application/json, */*, ...)
            field_name = request_body_item[0]
            value = request_body_item[1]

            function_name = self.get_function_producing_this_value(value)
            matching_data = (field_name, self.get_data_matching_value(value))

            if function_name and matching_data:
                matching_functions_and_fields[function_name].append(matching_data)

        return matching_functions_and_fields

    def get_function_producing_this_value(self, value: str) -> str | None:
        for function_name, response_data in self.function_names_and_their_responses.items():
            if self.is_found_in_data(value, response_data):
                return function_name

    @staticmethod
    def is_found_in_data(
        value: str, data: dict[str, str] | list[dict[str, str]]
    ) -> bool:
        for response in data:
            values = list(response.values())
            if value in values:
                return True

        return False

    def get_data_matching_value(self, value: str) -> tuple[str, int | None] | None:
        for response in self.function_names_and_their_responses.values():
            # if the response is a list, add index to tuple
            if isinstance(response, list):
                return self.get_field_name_and_index_where_values_match(
                    value, response, True
                )

            else:
                return self.get_field_name_and_index_where_values_match(
                    value, response, False
                )

    @staticmethod
    def get_field_name_and_index_where_values_match(
        value: str, response: dict[str, str] | list[dict[str, str]], has_index=True
    ) -> tuple[str, int | None] | None:
        for index, data_dict in enumerate(response):
            if data_dict:
                for field_name, response_value in data_dict.items():
                    # request_field_name = request_body_item[0]
                    # value = request_body_item[1]
                    #
                    if value == response_value:
                        if has_index:
                            return_tuple = (request_field_name, (field_name, index))
                        else:
                            return_tuple = (request_field_name, (field_name, None))

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
