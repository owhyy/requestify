from requestify import (
    RequestifyList,
    REQUESTS_CLASS_NAME,
    RESPONSE_VARIABLE_NAME,
    REQUEST_VARIABLE_NAME,
    RequestifyObject,
)
import asyncio
from utils import get_response, get_responses, beautify_string, is_valid_response

RESPONSES_DICT_NAME = "workflow"
HEADERS_DICT_NAME = "h_workflow"
JSON_ERROR_NAME = "JSONDecodeError"


class ReplaceRequestify(RequestifyList):
    """
    Class handling the conversion of cURL requests to requests library requests,
    with data replaced by the previously matching returned data.
    """

    def __init__(self, base_list):
        """
        Parameters
        ----------
        base_list : list(str)
            List of cURL requests
        """

        super().__init__(base_list)

        self.names_and_responses = {}
        self.headers_workflow = {}
        self.functions_called = {}
        self.matching_field_names = {}

        self.__generate()

    def __generate(self):
        # self.init_first_response()
        self.initialize_responses_dict()

        self.initialize_matching_stuff()

    # def init_first_response(self):
    #     for requestify_object in self.requests:
    #         response = get_response(requestify_object)
    #
    #         if is_valid_response(response):
    #             self.map_response_to_current_function(
    #                 requestify_object.function_name, response
    #             )
    #
    def add_new_request(self, requestify_object):
        response = get_response(requestify_object)

        if is_valid_response(response):
            self.map_response_to_current_function(
                requestify_object.function_name, response
            )

    def map_response_to_current_function(self, function_name, response):
        if not isinstance(response, str):
            self.names_and_responses[function_name] = response

    def initialize_responses_dict(self):
        assert len(self.requests) > 0, "There must be at least one request"

        responses = get_responses(self.requests)

        for request, response in zip(self.requests, responses):
            self.map_response_to_current_function(request.function_name, response)

    def initialize_matching_stuff(self):
        for requestify_object in self.requests:
            function_with_response_matching_data = ""
            matching_request_field_names = []
            matching_response_field_names = []
            current_function = requestify_object.function_name

            for field_name, data_value in requestify_object.data.items():
                for function_name, response_data in self.names_and_responses.items():
                    # ignore current function's returned data
                    if function_name == current_function:
                        continue
                    if ReplaceRequestify.found_in_list(data_value, response_data):
                        self.functions_called[current_function] = function_name
                        matching_request_field_names.append(field_name)
                        matching_response_field_names.append(
                            ReplaceRequestify.get_field_name_and_index(
                                data_value, response_data
                            )
                        )

                        function_with_response_matching_data = function_name

                    elif ReplaceRequestify.found_in_dict(data_value, response_data):
                        self.functions_called[current_function] = function_name
                        matching_request_field_names.append(field_name)
                        matching_response_field_names.append(
                            ReplaceRequestify.get_field_name_matching_value(
                                data_value, response_data
                            )
                        )

                        function_with_response_matching_data = function_name

                    else:
                        break


            self.map_matching_stuff_to_current_function(
                current_function,
                matching_request_field_names,
                matching_response_field_names,
                function_with_response_matching_data,
            )

    @staticmethod
    def found_in_list(value, list_of_data):
        return isinstance(list_of_data, list) and ReplaceRequestify.is_in_list_of_dicts(
            value, list_of_data
        )

    @staticmethod
    def is_in_list_of_dicts(value, list_of_dicts):
        for dict in list_of_dicts:
            if value in dict.values():
                return True

        return False

    @staticmethod
    def found_in_dict(value, data_dict):
        return isinstance(data_dict, dict) and value in data_dict.values()

    @staticmethod
    def get_field_name_and_index(sought_value, list_of_dicts):
        for index, dict in enumerate(list_of_dicts):
            ret = ReplaceRequestify.get_field_name_matching_value(sought_value, dict)
            if ret:
                return (ret, index)

    @staticmethod
    def get_field_name_matching_value(sought_value, dict):
        for field_name, value in dict.items():
            if sought_value == value:
                return field_name

    def map_matching_stuff_to_current_function(
        self,
        function_name,
        matching_request_field_names,
        matching_response_field_names,
        function_called,
    ):
        if (
            function_name
            and matching_request_field_names
            and matching_response_field_names
            and function_called
        ):
            for request_field, response_field in zip(
                matching_request_field_names, matching_response_field_names
            ):
                self.matching_field_names.setdefault((function_name, function_called), []).append(
                    (
                        request_field,
                        response_field,
                    )
                )

    def map_matching_fields_to_current_function(
        self, function_name, matching_request_field_names, matching_response_field_names
    ):
        if (
            function_name
            and matching_request_field_names
            and matching_response_field_names
        ):
            for request_field, response_field in zip(
                matching_request_field_names, matching_response_field_names
            ):
                self.matching_field_names.setdefault(function_name, []).append(
                    (
                        request_field,
                        response_field,
                    )
                )

    def map_matching_response_function_to_current_function(
        self, function_name, function_called
    ):
        """
        Maps the name of the function that returned data
        which matched to some value in current function's data or headers
        """
        self.functions_called[function_name] = function_called

    def __create_responses_text(self, with_headers=True, with_cookies=True):
        indent = "\t\t"

        requests_text = [
            "import requests",
            "import pprint",
            f"from json import {JSON_ERROR_NAME}",
            f"class {REQUESTS_CLASS_NAME}():",
            "\tdef __init__(self):",
            f"\t\tself.{RESPONSES_DICT_NAME} = {{}}",
        ]

        for request in self.requests:
            response = request.create_responses_base(
                indent=indent,
                with_headers=with_headers,
                with_cookies=with_cookies,
            )

            function_called = self.functions_called.get(request.function_name)

            if request.data:
                matching_fields = self.matching_field_names[(request.function_name)]
                nonmatching_fields = [
                    field_name
                    for field_name, _ in request.data.items()
                    if field_name not in matching_fields
                ]

                request_field_names = [field[0] for field in matching_fields]
                response_field_names = [field[1] for field in matching_fields]

                new_data = f"{indent}data = {{"
                for request_field_name, response_field_name in zip(
                    request_field_names, response_field_names
                ):
                    if isinstance(response_field_name, str):
                        new_data += f"'{request_field_name}': self.{RESPONSES_DICT_NAME}['{function_called}']['{response_field_name}'], "
                    elif isinstance(response_field_name, tuple):
                        new_data += f"'{request_field_name}': self.{RESPONSES_DICT_NAME}['{function_called}']['{response_field_name[0]}'][{response_field_name[1]}], "

                for name, value in request.data.items():
                    if name not in request_field_names:
                        new_data += f"'{name}': value, "

                new_data += "}\n"
                # if the request has a data field, in the generated response it will be the last field
                response[-2] = new_data
                # response[-2] = new_data

            final_response = "\n".join(response)

            requests_text.append(
                f"\tdef {request.function_name}(self):{final_response}"
            )
            requests_text.append(
                "\n\t\t".join(
                    [
                        "\t\ttry:",
                        f"\t{RESPONSE_VARIABLE_NAME}={REQUEST_VARIABLE_NAME}.json()",
                        f"\tpprint.pprint({REQUEST_VARIABLE_NAME}.json())",
                        f"except {JSON_ERROR_NAME}:",
                        f"\t{RESPONSE_VARIABLE_NAME}={REQUEST_VARIABLE_NAME}.text",
                        f"\tpprint.pprint({REQUEST_VARIABLE_NAME}.text)\n",
                    ]
                )
            )

            requests_text.append(
                f"\t\tself.{RESPONSES_DICT_NAME}['{request.function_name}']={RESPONSE_VARIABLE_NAME}"
            )

        requests_text.append("\tdef call_all(self):")
        requests_text.append(
            "".join(
                f"\t\tself.{function_name}()\n"
                for function_name in self.existing_function_names
            )
        )
        requests_text.append("if __name__ == '__main__': ")
        requests_text.append(f"\t{REQUESTS_CLASS_NAME}().call_all()")
        return beautify_string("\n".join(requests_text))

    def __write_to_stdio(self, with_headers=True, with_cookies=True):
        requests_as_functions = self.__create_responses_text(
            with_headers=with_headers, with_cookies=with_cookies
        )
        print(requests_as_functions)

    def to_screen(self):
        self.__write_to_stdio()
