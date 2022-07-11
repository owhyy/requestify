from collections import defaultdict
from requestify import (
    RequestifyList,
    REQUESTS_CLASS_NAME,
    RESPONSE_VARIABLE_NAME,
    REQUEST_VARIABLE_NAME,
    RequestifyObject,
)
import asyncio
from pprint import pprint
from text_utils import (
    generate_imports_text,
    indent_function_inside_class,
    indent_function_inside_class,
    generate_function_text_inside_class,
    generate_function_text_outside_class,
    indent_class,
    generate_class_text,
)

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
    # def add_new_request(self, requestify_object):
    #     response = get_response(requestify_object)
    #
    #     if is_valid_response(response):
    #         self.map_response_to_current_function(
    #             requestify_object.function_name, response
    #         )

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

    def map_all_functions_to_their_responses(self, responses):
        for request, response in zip(self.requests, responses):
            self.map_response_to_current_function(request.function_name, response)

    def initialize_responses_dict(self):
        assert len(self.requests) > 0, "There must be at least one request"

        responses = get_responses(self.requests)
        self.map_all_functions_to_their_responses(responses)

    def get_field_pair_where_values_matches(self, request_body_item):
        for response in self.function_names_and_responses.values():
            has_index = False

            if len(response) != 1:
                has_index = True

            for index, json_item in enumerate(response):
                if json_item:
                    for field_name, response_value in json_item.items():
                        request_field_name = request_body_item[0]
                        value = request_body_item[1]

                        if value == response_value:
                            if has_index:
                                return_tuple = (request_field_name, (field_name, index))
                            else:
                                return_tuple = (request_field_name, (field_name, None))

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

    @staticmethod
    def add_index_if_needed(data_string, index):
        data_string_with_index = ""
        if index is not None:
            data_string_with_index = data_string + f"[{index}],"
        else:
            data_string_with_index = data_string + ","

        return data_string_with_index

    def format_data_line(self, matching_data):
        data_string_with_index = ""
        data_parts = [f"data={{"]

        for function_called, list_of_fields in matching_data.items():
            for request_field, (response_field, index) in list_of_fields:
                data_part = f"'{request_field}': {RESPONSES_DICT_NAME}['{function_called}']['{response_field}']"
                data_string_with_index = ReplaceRequestify.add_index_if_needed(
                    data_part, index
                )

                data_parts.append(data_string_with_index)

        data_string_with_index += "}"
        return "\n".join(data_parts)

    @staticmethod
    def replace_response_data(response_as_list, formatted_data_line, has_data=False):
        response_with_replaced_data = response_as_list

        if has_data:
            response_with_replaced_data[2] = formatted_data_line

        return response_with_replaced_data

    @staticmethod
    def replace_response_containing_data(response_as_list, formatted_data_line):
        return ReplaceRequestify.replace_response_data(
            response_as_list, formatted_data_line, has_data=True
        )

    @staticmethod
    def replace_response_not_containing_data(response_as_list, formatted_data_line):
        return ReplaceRequestify.replace_response_data(
            response_as_list, formatted_data_line, has_data=True
        )

    def get_formatted_response(self, request):
        base_response = super().create_base_response(request=request)
        matching_data = self.matching_data.get(request.function_name)

        data_line = self.format_data_line(matching_data=matching_data)
        base_response[2] = data_line

        if request.data:
            formatted_response = ReplaceRequestify.replace_response_containing_data(
                base_response, data_line
            )
        else:
            formatted_response = ReplaceRequestify.replace_response_not_containing_data(
                base_response, data_line
            )

        pprint(formatted_response)

    def get_replaced_functions(self):
        base_text = super().__create_base_response()

    def __create_responses_text(self, with_headers=True, with_cookies=True):

        requests_text = [
            generate_imports_text(["requests", "pprint"]),
            generate_class(
                REQUESTS_CLASS_NAME,
            ),  # < should be all the functions
        ]

    def __write_to_stdio(self, with_headers=True, with_cookies=True):
        requests_as_functions = self.__create_responses_text(
            with_headers=with_headers, with_cookies=with_cookies
        )
        print(requests_as_functions)

    def debug(self):
        request = self.requests[2]
        self.get_formatted_response(request)

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
