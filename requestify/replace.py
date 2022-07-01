from requestify import (
    RequestifyList,
    REQUESTS_CLASS_NAME,
    REQUEST_VARIABLE_NAME,
    __get_file,
    RequestifyObject,
)
from black import format_str, FileMode
import json

RESPONSES_DICT_NAME = "workflow"
RESPONSE_VARIABLE_NAME = "response"


# class ReplaceRequestifyObjecet(RequestifyObject):
#     def __create_responses_base(self, indent="", with_headers=True, with_cookies=True):
#         if self.data:
#             pass
#         else:
#             .__create_responses_base(indent=indent,with_headers=with_headers, with_cookies=with_cookies)


class ReplaceRequestify(RequestifyList):
    def __init__(self, base_list):
        RequestifyList.__init__(self, base_list)
        self.workflow = dict()
        self.methods_called = []
        self.generate_workflow()

    def generate_workflow(self):
        for request in self.requests:
            self.workflow[request.create_function_name()] = request.execute()

    def match_data(self, request):
        # for every value in the request's data
        for value in list(request.data.values()):
            # for every response returned before
            for function_name, w_dict in self.workflow.items():
                # for every value of this actual response
                for w_value in list(w_dict.values()):
                    # if the request data's value matches the response's values
                    if value == w_value:
                        # set the request's data body to the request returned
                        request.data = w_dict.items()
                        self.methods_called.append(function_name)
                        break
                # so it breaks of all the fors
                else:
                    continue
                break
            else:
                continue
            break

    def create_responses_text(self, with_headers=True, with_cookies=True):
        requests_text = [
            "import requests",
            "\n\n",
            f"class {REQUESTS_CLASS_NAME}():",
            "\n",
            f"\t{RESPONSES_DICT_NAME} = dict()" "\n",
        ]
        function_names = []

        for request in self.requests:
            function_name = request.create_function_name()
            function_names.append(function_name)

            self.match_data(request)

            response = request.create_responses_base(
                indent="\t\t", with_headers=with_headers, with_cookies=with_cookies
            )

            requests_text.append(f"\tdef {function_name}(self):{response}")
            requests_text.append(
                f"\t\t{RESPONSE_VARIABLE_NAME}={REQUEST_VARIABLE_NAME}.text"
            )
            requests_text.append(
                f"\t\tself.{RESPONSES_DICT_NAME}['{function_name}']={RESPONSE_VARIABLE_NAME}"
            )

            # requests_text.append("\n")

        requests_text.append("\tdef call_all(self):")
        requests_text.append(
            "".join(
                [f"\t\tself.{function_name}()\n" for function_name in function_names]
            )
        )

        requests_text.append("if __name__ == '__main__': ")
        requests_text.append(f"\t{REQUESTS_CLASS_NAME}().call_all()")
        # return format_str("\n".join(requests_text), mode=FileMode())
        return "\n".join(requests_text)

    # def get_result(self, request):

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
