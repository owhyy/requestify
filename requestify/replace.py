from requestify import (
    RequestifyList,
    REQUESTS_CLASS_NAME,
    RESPONSE_VARIABLE_NAME,
    __get_file,
    RequestifyObject,
)
from black import format_str, FileMode
import json

RESPONSES_DICT_NAME = "workflow"

class ReplaceRequestify(RequestifyList):
    def __init__(self, base_list):
        RequestifyList.__init__(self, base_list)
        self.workflow = dict()
        self.methods_called = []
        self.generate_workflow()

    """
    Generates a dict containing the name of the called function and the result of calling it
    """
    def generate_workflow(self):
        assert len(self.requests) > 1, "There must be at least one request"

        request = self.requests[0]
        response = request.execute()

        self.workflow[request.function_name] = response if not isinstance(response, str) else None

        for request in self.requests[1:]:
            self.replace_data(request)
            response = request.execute()
            # only add json responses
            self.workflow[request.function_name] = response if not isinstance(response, str) else None

    def search_in_list(self, value, list_of_dicts):
        for dict in list_of_dicts:
            if value in dict.values():
                return dict

    def replace_data(self, request):
        data = None
        for value in list(request.data.values()):
            # stop the first time you match anything
            if data:
                break
            for function_name, returned_data in self.workflow.items():
                if isinstance(returned_data, list):
                    data = self.search_in_list(value, returned_data)
                elif isinstance(returned_data, dict):
                    if value in returned_data.values():
                        data = returned_data

        request.data = data

    def create_responses_text(self, with_headers=True, with_cookies=True):
        requests_text = [
            "import requests",
            "\n\n",
            f"class {REQUESTS_CLASS_NAME}():",
            "\n",
            f"\t{RESPONSES_DICT_NAME} = {self.workflow}" "\n",
        ]
        function_names = []

        for request in self.requests:
            function_name = RequestifyList.create_function_name(request) # this is not working
            function_names.append(function_name)

            response = request.create_responses_base(
                indent="\t\t", with_headers=with_headers, with_cookies=with_cookies
            )

            requests_text.append(f"\tdef {function_name}(self):{response}")
            # requests_text.append(
            #     f"\t\t{RESPONSE_VARIABLE_NAME}={REQUEST_VARIABLE_NAME}.text"
            # )
            # requests_text.append(
            #     f"\t\tself.{RESPONSES_DICT_NAME}['{function_name}']={RESPONSE_VARIABLE_NAME}"
            # )

            # requests_text.append("\n")

        requests_text.append("\tdef call_all(self):")
        requests_text.append(
            "".join(
                [f"\t\tself.{function_name}()\n" for function_name in function_names]
            )
        )

        requests_text.append("if __name__ == '__main__': ")
        requests_text.append(f"\t{REQUESTS_CLASS_NAME}().call_all()")
        return RequestifyObject.beautify_string("\n".join(requests_text))

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
