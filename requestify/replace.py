from requestify import (
    RequestifyList,
    REQUESTS_CLASS_NAME,
    RESPONSE_VARIABLE_NAME,
    REQUEST_VARIABLE_NAME,
    __get_file,
    RequestifyObject,
    beautify_string,
)
from black import format_str, FileMode
import json
from httpx import AsyncClient
import asyncio

RESPONSES_DICT_NAME = "workflow"
JSON_ERROR_NAME = "JSONDecodeError"


async def async_get_responses(requests):
    responses = []

    async with AsyncClient() as client:
        r = (
            client.request(
                method=request.method,
                url=request.url,
                headers=request.headers,
                cookies=request.cookies,
            )
            for request in requests
        )
        tasks = await asyncio.gather(*r)

    for task in tasks:
        try:
            responses.append(task.json())
        except json.JSONDecodeError:
            responses.append(task.text)

    return responses


class ReplaceRequestify(RequestifyList):
    def __init__(self, base_list):
        super().__init__(base_list)
        self.workflow = dict()
        self.functions_called = dict()
        self.matching_field_names = dict()
        self.generate_workflow_async()

    """
    Generates a dict containing the name of the called function and the result of calling it
    """

    def generate_workflow_async(self):
        assert len(self.requests) > 1, "There must be at least one request"
        responses = asyncio.run(async_get_responses(self.requests))

        for response, request in zip(responses, self.requests):
            self.replace_data(request)
            self.workflow[request.function_name] = (
                response if not isinstance(response, str) else None
            )

    def generate_workflow(self):
        assert len(self.requests) > 1, "There must be at least one request"

        request = self.requests[0]
        response = request.execute()

        self.workflow[request.function_name] = (
            response if not isinstance(response, str) else None
        )

        for request in self.requests[1:]:
            self.replace_data(request)
            response = request.execute()
            # only add json responses
            self.workflow[request.function_name] = (
                response if not isinstance(response, str) else None
            )

    def search_in_list(self, value, list_of_dicts):
        for dict in list_of_dicts:
            if value in dict.values():
                return True

    def matching_field_in_list(self, value, list_of_dicts):
        for dict in list_of_dicts:
            if value in dict.values():
                for field_name, _ in dict.items():
                    if value == _:
                        return field_name

    def replace_data(self, request):
        # data = None
        function_called = ""
        matching_request_field_name = ""
        matching_response_field_name = ""

        for request_field_name, value in list(request.data.items()):
            # stop the first time you match anything
            # if data:
            #     break

            for function_name, returned_data in self.workflow.items():
                if isinstance(returned_data, list):
                    found_in_list = self.search_in_list(value, returned_data)
                    function_called = function_name if found_in_list else ""
                    matching_request_field_name = request_field_name
                    matching_response_field_name = self.matching_field_in_list(
                        value, returned_data
                    )
                    # data = self.search_in_list(value, returned_data)
                elif isinstance(returned_data, dict):
                    if value in returned_data.values():
                        function_called = function_name
                        matching_request_field_name = request_field_name
                        for field_name, _ in returned_data.items():
                            if value == _:
                                matching_response_field_name = field_name
                                break
                        # data = returned_data

        self.functions_called[request.function_name] = function_called

        # this adds to the list of tuples, each tuple representing the request and response's field names where the value matches
        self.matching_field_names.setdefault(request.function_name, []).append(
            (
                matching_request_field_name,
                matching_response_field_name,
            )
        )

    def create_responses_text(self, with_headers=True, with_cookies=True):
        indent = "\t\t"

        requests_text = [
            "import requests",
            "\n",
            "import pprint",
            "\n",
            f"from json import {JSON_ERROR_NAME}",
            "\n\n",
            f"class {REQUESTS_CLASS_NAME}():",
            "\n",
            "\tdef __init__(self):\n",
            f"\t\tself.{RESPONSES_DICT_NAME} = {{}}" "\n",
        ]

        for request in self.requests:
            response = request.create_responses_base(
                indent=indent,
                with_headers=with_headers,
                with_cookies=with_cookies,
            )

            function_called = self.functions_called.get(request.function_name)
            if function_called:
                if request.data:
                    # data is always last
                    matching_fields = self.matching_field_names[request.function_name]

                    request_field_names = [field[0] for field in matching_fields]
                    response_field_names = [field[1] for field in matching_fields]

                    for request_field_name, response_field_name in zip(
                        request_field_names, response_field_names
                    ):
                        new_data = f"{indent}data = {{'{request_field_name}': self.{RESPONSES_DICT_NAME}['{function_called}']['{response_field_name}']}}\n"
                    response[-2] = new_data

            final_response = "\n".join(response)

            requests_text.append(
                f"\tdef {request.function_name}(self):{final_response}"
            )
            requests_text.append(
                f"\t\ttry: \n"
                f"\t\t\t{RESPONSE_VARIABLE_NAME}={REQUEST_VARIABLE_NAME}.json()\n"
                f"\t\t\tpprint.pprint({REQUEST_VARIABLE_NAME}.json())\n"
                f"\t\texcept {JSON_ERROR_NAME}:\n"
                f"\t\t\t{RESPONSE_VARIABLE_NAME}={REQUEST_VARIABLE_NAME}.text\n"
                f"\t\t\tpprint.pprint({REQUEST_VARIABLE_NAME}.text)\n"
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
