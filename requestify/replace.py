from requestify import (
    RequestifyList,
    REQUESTS_CLASS_NAME,
    RESPONSE_VARIABLE_NAME,
    REQUEST_VARIABLE_NAME,
    __get_file,
    RequestifyObject,
)
import asyncio
from utils import get_responses, get_responses_async, beautify_string

RESPONSES_DICT_NAME = "workflow"
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

        self.workflow = dict()
        self.functions_called = dict()
        self.matching_field_names = dict()

        self.__generate()
        self.generate_workflow_async()

    def map_response_to_current_function(self, function_name, response):
        if not isinstance(response, str):
            self.workflow[function_name] = response

    def map_matching_fields_to_current_function(
        self, function_name, matching_request_field_name, matching_response_field_name
    ):
        if (
            function_name
            and matching_request_field_name
            and matching_response_field_name
        ):
            self.matching_field_names.setdefault(function_name, []).append(
                (
                    matching_request_field_name,
                    matching_response_field_name,
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

    def map_matching_stuff_to_current_function(
        self,
        function_name,
        matching_request_field_name,
        matching_response_field_name,
        function_called,
    ):
        if (
            function_name
            and matching_request_field_name
            and matching_response_field_name
            and function_called
        ):
            self.map_matching_fields_to_current_function(
                function_name, matching_request_field_name, matching_response_field_name
            )
            self.map_matching_response_function_to_current_function(
                function_name, function_called
            )

    def __generate(self):
        self.initialize_matching_stuff()
        self.generate_workflow_async()

    def generate_workflow_async(self):
        assert len(self.requests) > 0, "There must be at least one request"

        responses = asyncio.run(get_responses_async(self.requests))

        for requestify_object, response in zip(self.requests, responses):
            self.map_response_to_current_function(
                requestify_object.function_name, response
            )

    def generate_workflow(self):
        assert len(self.requests) > 0, "There must be at least one request"

        responses = get_responses(self.requests)

        for request, response in zip(self.requests, responses):
            self.map_response_to_current_function(request.function_name, response)

    @staticmethod
    def is_in_list_of_dicts(value, list_of_dicts):
        return (value in dict.values() for dict in list_of_dicts)

    @staticmethod
    def get_all_field_names_matching_value(sought_value, list_of_dicts):
        return (
            ReplaceRequestify.get_field_name_matching_value(sought_value, dict)
            for dict in list_of_dicts
        )

    @staticmethod
    def get_field_name_matching_value(sought_value, dict):
        return (
            field_name for field_name, value in dict.items() if sought_value == value
        )

    @staticmethod
    def found_in_list(value, list):
        return isinstance(list, list) and ReplaceRequestify.is_in_list_of_dicts(value, list)

    @staticmethod
    def found_in_dict(value, dict):
        return isinstance(dict, dict) and value in dict.values()

    def initialize_matching_stuff(self):
        for requestify_object in self.requests:
            function_with_response_matching_data = ""
            matching_request_field_name = ""
            matching_response_field_name = ""
            current_function = requestify_object.function_name

            for field_name, data_value in list(requestify_object.data.items()):
                for function_name, response_data in self.workflow.items():
                    if ReplaceRequestify.found_in_list(response_data, data_value):
                        function_with_response_matching_data = function_name

                        matching_request_field_name = field_name
                        matching_response_field_name = (
                            ReplaceRequestify.get_all_field_names_matching_value(
                                data_value, response_data
                            )
                        )

                    elif ReplaceRequestify.found_in_dict(data_value, response_data):
                        function_with_response_matching_data = function_name

                        matching_request_field_name = field_name
                        matching_response_field_name = (
                            ReplaceRequestify.get_field_name_matching_value(
                                data_value, response_data
                            )
                        )

            self.map_matching_stuff_to_current_function(
                current_function,
                matching_request_field_name,
                matching_response_field_name,
                function_with_response_matching_data,
            )

    def create_responses_text(self, with_headers=True, with_cookies=True):
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

            if function_called:
                # if the request has
                if request.data:
                    # data is always last
                    matching_fields = self.matching_field_names[request.function_name]

                    request_field_names = [field[0] for field in matching_fields]
                    response_field_names = [field[1] for field in matching_fields]

                    for request_field_name, response_field_name in zip(
                        request_field_names, response_field_names
                    ):
                        new_data = f"{indent}data = {{'{request_field_name}': self.{RESPONSES_DICT_NAME}['{function_called}']['{response_field_name}']}}\n"
                        # response[-2] = new_data
                    response[-2] = new_data

            final_response = "\n".join(response)

            requests_text.append(
                f"\tdef {request.function_name}(self):{final_response}"
            )
            requests_text.append(
                "\n\t\t".join([
                "\t\ttry:",
                f"\t{RESPONSE_VARIABLE_NAME}={REQUEST_VARIABLE_NAME}.json()",
                f"\tpprint.pprint({REQUEST_VARIABLE_NAME}.json())",
                f"except {JSON_ERROR_NAME}:",
                f"\t{RESPONSE_VARIABLE_NAME}={REQUEST_VARIABLE_NAME}.text",
                f"\tpprint.pprint({REQUEST_VARIABLE_NAME}.text)\n"])
            )

            function_called = self.functions_called.get(request.function_name)
            matching_field_names = self.matching_field_names.get(request.function_name)

            requests_text.append(
                f"\t\tself.{RESPONSES_DICT_NAME}['{request.function_name}']={RESPONSE_VARIABLE_NAME}"
            )
            # if function_called:
            #     requests_text.append(
            #         f"\t\tself.{RESPONSES_DICT_NAME}['{self.functions_called[request.function_name]}']={RESPONSE_VARIABLE_NAME}"
            #     )

            # requests_text.append("\n")

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
        # return "\n".join(requests_text)

    def __write_to_stdio(self, with_headers=True, with_cookies=True):
        requests_as_functions = self.create_responses_text(
            with_headers=with_headers, with_cookies=with_cookies
        )
        print(requests_as_functions)

    def to_screen(self):
        self.__write_to_stdio()


def from_string(string):
    return ReplaceRequestify([string])


def from_file(filename):
    requests_from_file = __get_file(filename)
    assert requests_from_file, "No data in the specified file"
    if len(requests_from_file) == 1:
        requests = RequestifyObject(requests_from_file[0])
    else:
        requests = ReplaceRequestify(requests_from_file)
    return requests
