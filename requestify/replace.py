from collections import defaultdict
from requestify import (
    RequestifyList,
    REQUESTS_CLASS_NAME,
    RESPONSE_VARIABLE_NAME,
    REQUEST_VARIABLE_NAME,
    RequestifyObject,
)
import asyncio
import pprint
from utils import (
    get_response,
    get_responses,
    beautify_string,
    is_valid_response,
    is_json,
)

RESPONSES_DICT_NAME = "workflow"
HEADERS_DICT_NAME = "h_workflow"
JSON_ERROR_NAME = "JSONDecodeError"


class MatchRequestifyObject:
    def __init__(self, current_function, called_function, matching_fields):
        self.__current_function = current_function
        self.__called_function = called_function
        self.__matching_fields = matching_fields

    def get_current_function(self):
        return self.__current_function

    def get_called_function(self):
        return self.__called_function

    def get_matching_fields(self):
        return self.__matching_fields


class ReplaceRequestify(RequestifyList):
    """
    Class handling the conversion of cURL requests to requests library requests,
    with data replaced by the previously matching returned data.

    Attributes
    ----------
    function_names_and_responses : dict(str : str)
        a dict with the function name as key, and response of that function as value
    matching_data : list(MatchRequestifyObject)
        a list of dict-like objects with the function name as key, and the
        function called that produced some result values that matched, and
        the field name of the values that match

    """

    def __init__(self, base_list):
        """
        Parameters
        ----------
        base_list : list(str)
            List of cURL requests
        """

        super().__init__(base_list)

        self.function_names_and_responses = {}
        self.matching_data = {}
        # self.matching_headers = {}

        self.__generate()

    def __generate(self):
        # self.init_first_response()
        self.initialize_responses_dict()
        self.initialize_matching_data()

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

    @staticmethod
    def convert_response_to_list(response):
        """
        Makes our life easier when dealing with nested lists
        """
        if not isinstance(response, list):
            return [response]

        return response

    def map_response_to_current_function(self, function_name, response):
        if not isinstance(response, str):
            self.function_names_and_responses[
                function_name
            ] = ReplaceRequestify.convert_response_to_list(response)

    def initialize_responses_dict(self):
        assert len(self.requests) > 0, "There must be at least one request"

        responses = get_responses(self.requests)

        for request, response in zip(self.requests, responses):
            self.map_response_to_current_function(request.function_name, response)

    def get_field_pair_where_values_matches(self, request_body_item):
        for response in self.function_names_and_responses.values():
            has_index=False

            if len(response) != 1:
                has_index = True

            for index, json_item in enumerate(response):
                if json_item:
                    for field_name, response_value in json_item.items():
                        request_field_name = request_body_item[0]
                        value = request_body_item[1]

                        if value == response_value:
                            if has_index:
                                return_tuple = (request_field_name, field_name, index)
                            else:
                                return_tuple = (request_field_name, field_name)

                            return return_tuple

    def get_function_producing_this_value(self, value):
        for function_name, response_data in self.function_names_and_responses.items():
            if ReplaceRequestify.is_found_in_data(value, response_data):
                return function_name

    def get_functions_and_fields_matching_request_body(self, request_body):
        functions_and_fields = defaultdict(list)

        for request_body_item in request_body.items():
            value = request_body_item[1]

            function = self.get_function_producing_this_value(value)
            field = self.get_field_pair_where_values_matches(request_body_item)

            functions_and_fields[function].append(field)

        return functions_and_fields

    def initialize_matching_data(self):
        for request in self.requests:
            request_body = request.data
            current_function = request.function_name
            if request_body:
                matching_data = self.get_functions_and_fields_matching_request_body(
                    request_body
                )
                self.matching_data[current_function] = matching_data

    @staticmethod
    def is_found_in_data(value, data):
        for response in data:
            values = list(response.values())
            if value in values:
                return True

        return False

    @staticmethod
    def get_response_field_name_and_index(sought_value, list_of_dicts):
        for index, dict in enumerate(list_of_dicts):
            ret = ReplaceRequestify.get_field_name_matching_value(sought_value, dict)
            if ret:
                return (ret, index)

    @staticmethod
    def get_field_name_matching_value(sought_value, dict):
        for field_name, value in dict.items():
            if sought_value == value:
                return field_name

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

            current_function = request.function_name
            current_matches = [
                match
                for match in self.matching_data
                if match.get_current_function() == current_function
            ]

            for match in current_matches:
                current_called_function = match.get_called_function()
                current_field_names = [
                    match.get_matching_fields()
                    for match in current_matches
                    if match.get_called_function() == current_called_function
                ]

        #     if request.data:
        #         request_field_names = [field[0] for field in matching_fields]
        #         response_field_names = [field[1] for field in matching_fields]
        #
        #         new_data = f"{indent}data = {{"
        #         for request_field_name, response_field_name in zip(
        #             request_field_names, response_field_names
        #         ):
        #             if isinstance(response_field_name, str):
        #                 new_data += f"'{request_field_name}': self.{RESPONSES_DICT_NAME}['{function_called}']['{response_field_name}'], "
        #             elif isinstance(response_field_name, tuple):
        #                 new_data += f"'{request_field_name}': self.{RESPONSES_DICT_NAME}['{function_called}']['{response_field_name[0]}'][{response_field_name[1]}], "
        #
        #         for name, value in request.data.items():
        #             if name not in request_field_names:
        #                 new_data += f"'{name}': value, "
        #
        #         new_data += "}\n"
        #         # if the request has a data field, in the generated response it will be the last field
        #         response[-2] = new_data
        #         # response[-2] = new_data
        #
        #     final_response = "\n".join(response)
        #
        #     requests_text.append(
        #         f"\tdef {request.function_name}(self):{final_response}"
        #     )
        #     requests_text.append(
        #         "\n\t\t".join(
        #             [
        #                 "\t\ttry:",
        #                 f"\t{RESPONSE_VARIABLE_NAME}={REQUEST_VARIABLE_NAME}.json()",
        #                 f"\tpprint.pprint({REQUEST_VARIABLE_NAME}.json())",
        #                 f"except {JSON_ERROR_NAME}:",
        #                 f"\t{RESPONSE_VARIABLE_NAME}={REQUEST_VARIABLE_NAME}.text",
        #                 f"\tpprint.pprint({REQUEST_VARIABLE_NAME}.text)\n",
        #             ]
        #         )
        #     )
        #
        #     requests_text.append(
        #         f"\t\tself.{RESPONSES_DICT_NAME}['{request.function_name}']={RESPONSE_VARIABLE_NAME}"
        #     )
        #
        # requests_text.append("\tdef call_all(self):")
        # requests_text.append(
        #     "".join(
        #         f"\t\tself.{function_name}()\n"
        #         for function_name in self.existing_function_names
        #     )
        # )
        # requests_text.append("if __name__ == '__main__': ")
        # requests_text.append(f"\t{REQUESTS_CLASS_NAME}().call_all()")
        # return beautify_string("\n".join(requests_text))

    def __write_to_stdio(self, with_headers=True, with_cookies=True):
        requests_as_functions = self.__create_responses_text(
            with_headers=with_headers, with_cookies=with_cookies
        )
        print(requests_as_functions)

    def debug(self):
        # print(self.function_names_and_responses.items())
        pprint.pprint(self.matching_data)

    def to_screen(self):
        self.__write_to_stdio()


def __get_file(filename):
    requests = []
    request = ""
    with open(filename, mode="r") as in_file:
        for line in in_file:
            request += line
            if "curl" in line:
                requests.append(request)
                request = ""
    return requests


def from_file(filename, replace=False):
    requests_from_file = __get_file(filename)
    assert requests_from_file, "No data in the specified file"
    if len(requests_from_file) == 1:
        requests = RequestifyObject(requests_from_file[0])
    else:
        if replace:
            requests = ReplaceRequestify(requests_from_file)
        else:
            requests = RequestifyList(requests_from_file)
    return requests


from_file("../tests/test_files/test_data.txt", replace=True).debug()
