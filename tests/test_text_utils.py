import pytest
from requestify.models import _RequestifyObject, _RequestifyList, _ReplaceRequestify
from requestify import text_utils
from .helpers import mock_get_responses

GOOGLE = "https://google.com"


@pytest.fixture
def unindented_function():
    return ("def function_name():", ['print("i am a function body")'])


class TestBaseGeneration:
    def test_generate_imports(self):
        assert text_utils.generate_imports_text("unittest", "numpy", "json") == [
            "import unittest",
            "import numpy",
            "import json",
        ]

    def test_generate_imports_no_args(self):
        assert len(text_utils.generate_imports_text()) == 0

    def test_replace_function_name(self):
        pass

    def test_generate_function_text_inside_class(self):
        function_in_class = (
            "\tdef function_name(self):",
            [
                '\t\tprint("i am a function body")',
                '\t\tprint("this is another line")',
                "\t\tx=10",
            ],
        )
        assert (
            text_utils.generate_function_text_inside_class(
                "function_name",
                'print("i am a function body")',
                'print("this is another line")',
                "x=10",
            )
            == function_in_class
        )

    def test_generate_function_text_outside_class(self):
        function_outside_class = (
            "def function_name():",
            [
                '\tprint("i am a function body")',
                '\tprint("this is another line")',
                "\tx=10",
            ],
        )
        assert (
            text_utils.generate_function_text_outside_class(
                "function_name",
                'print("i am a function body")',
                'print("this is another line")',
                "x=10",
            )
            == function_outside_class
        )

    def test_indent_function_inside_class(self, unindented_function):
        indented_function = (
            "\tdef function_name():",
            [
                '\t\tprint("i am a function body")',
            ],
        )
        assert (
            text_utils.indent_function_inside_class(unindented_function)
            == indented_function
        )

    def test_indent_function_outside_class(self, unindented_function):
        indented_function = (
            "def function_name():",
            [
                '\tprint("i am a function body")',
            ],
        )
        assert (
            text_utils.indent_function_outside_class(unindented_function)
            == indented_function
        )

    def test_indent_class_body(self):
        unindented_class_function = (
            "def function_name(self):",
            [
                'print("i am a function body")',
            ],
        )

        indented_class_function = (
            "\tdef function_name(self):",
            [
                '\t\tprint("i am a function body")',
            ],
        )
        # unindented_class_body = [unindented_class_function] * 3
        # indented_class_body = [indented_class_function] * 3

        assert text_utils.indent_class_body(unindented_class_function) == [
            indented_class_function
        ]

    def test_generate_class_from_generated_functions(self):
        unindented_class_function = (
            "def function_name(self):",
            [
                'print("i am a function body")',
            ],
        )
        indented_class_function = (
            "\tdef function_name(self):",
            [
                '\t\tprint("i am a function body")',
            ],
        )
        assert text_utils.generate_class_text_from_generated_functions(
            "SomeClass", unindented_class_function, unindented_class_function
        ) == ("class SomeClass():", [indented_class_function, indented_class_function])

    def test_generate_class_functions_from_ungenerated_functions(self):
        function = ("function_name", "foo = bar", "bar = foo")
        assert text_utils.generate_class_text_from_ungenerated_functions(
            "baz", function
        ) == (
            "class baz():",
            [("\tdef function_name(self):", ["\t\tfoo = bar", "\t\tbar = foo"])],
        )


class TestModelTextGeneration(object):
    @staticmethod
    def is_in_2d_list(s: str, l: list[str]):
        return any(s in sl for sl in l)

    def test_request_variable_name_gets_set(self):
        req = _RequestifyObject(f"""curl -X post '{GOOGLE}' -H 'x: y'""")
        assert self.is_in_2d_list(
            text_utils.REQUEST_VARIABLE_NAME,
            text_utils.generate_requestify_base_text(req, True, True),
        )

    def test_requestify_object_class_name_gets_set(self):
        req = _RequestifyObject(f"""curl -X post '{GOOGLE}' -H 'x: y'""")
        assert (
            text_utils.REQUEST_CLASS_NAME
            in text_utils.generate_requestify_class(req, True, True)[0]
        )

    def test_requestify_list_class_name_gets_set(self):
        rl = _RequestifyList(f"""curl -X post '{GOOGLE}' -H 'x: y'""")
        assert (
            text_utils.REQUEST_CLASS_NAME
            in text_utils.generate_requestify_list_class(rl, True, True)[0]
        )

    def test_requestify_object_function_name_gets_set(self):
        req = _RequestifyObject(f"""curl -X post '{GOOGLE}' -H 'x: y'""")
        assert (
            req._function_name
            in text_utils.generate_requestify_function(req, True, True)[0]
        )

    def test_requestify_list_function_name_gets_set(self):
        rl = _RequestifyList(f"""curl -X post '{GOOGLE}' -H 'x: y'""")
        assert (
            rl._requests[0]._function_name
            in text_utils.generate_requestify_list_function(rl, True, True)[0][0]
        )

    def test_base_requstify_with_headers_with_cookies(self):
        req = _RequestifyObject(f"""curl -X post '{GOOGLE}' -H 'x: y'""")
        base_response_text = [
            "headers = {'x': 'y'}",
            "cookies = {}",
            f"{text_utils.REQUEST_VARIABLE_NAME} = requests.{req._method}('{req._url}', headers=headers, cookies=cookies)",
        ]
        assert (
            text_utils.generate_requestify_base_text(req, True, True)
            == base_response_text
        )

    def test_base_requestify_no_headers_no_cookies(self):
        req = _RequestifyObject(f"curl -X GET '{GOOGLE}'")
        base_response_text = [
            f"{text_utils.REQUEST_VARIABLE_NAME} = requests.get('{GOOGLE}')",
        ]
        assert (
            text_utils.generate_requestify_base_text(
                req, with_headers=False, with_cookies=False
            )
            == base_response_text
        )

    def test_generate_requestify_function(self):
        req = _RequestifyObject(f"curl -X GET '{GOOGLE}'")
        text = (
            f"def {req._function_name}():",
            [
                "\theaders = {}",
                "\tcookies = {}",
                f"\t{text_utils.REQUEST_VARIABLE_NAME} = requests.get('{GOOGLE}', headers=headers, cookies=cookies)",
            ],
        )
        assert text_utils.generate_requestify_function(req) == text

    def test_generate_requestify_class(self):
        req = _RequestifyObject(f"curl -X GET '{GOOGLE}")
        text = (
            f"class {text_utils.REQUEST_CLASS_NAME}():",
            [
                (
                    f"\tdef {req._function_name}(self):",
                    [
                        "\t\theaders = {}",
                        "\t\tcookies = {}",
                        f"\t\t{text_utils.REQUEST_VARIABLE_NAME} = requests.get('{GOOGLE}', headers=headers, cookies=cookies)",
                    ],
                )
            ],
        )
        assert text_utils.generate_requestify_class(req) == text

    def test_generate_requestify_list_function(self):
        req = f"curl -X GET '{GOOGLE}"
        body = [
            "\theaders = {}",
            "\tcookies = {}",
            f"\t{text_utils.REQUEST_VARIABLE_NAME} = requests.get('{GOOGLE}', headers=headers, cookies=cookies)",
        ]

        rl = _RequestifyList(req)
        reqs = rl._requests
        text = [
            (f"def {reqs[0]._function_name}():", body),
        ]

        assert text_utils.generate_requestify_list_function(rl) == text

    def test_generate_requestify_list_class(self):
        req = f"curl -X GET '{GOOGLE}"
        rl = _RequestifyList(req)
        req = rl._requests
        text = (
            f"class {text_utils.REQUEST_CLASS_NAME}():",
            [
                (
                    f"\tdef {req[0]._function_name}(self):",
                    [
                        "\t\theaders = {}",
                        "\t\tcookies = {}",
                        f"\t\t{text_utils.REQUEST_VARIABLE_NAME} = requests.get('{GOOGLE}', headers=headers, cookies=cookies)",
                    ],
                )
            ],
        )
        assert text_utils.generate_requestify_list_class(rl) == text

    def test_generate_replacement_no_matching_data(self, mocker):
        mock_get_responses(mocker)
        rreq = _ReplaceRequestify(f"curl -X GET '{GOOGLE}")
        req = rreq._requests[0]
        text = (
            f"class {text_utils.REQUEST_CLASS_NAME}():",
            [
                (
                    "\tdef __init__(self):",
                    [
                        f"\t\tself.{text_utils.REQUEST_MATCHING_DATA_DICT_NAME} = {rreq._requests_and_their_responses}"
                    ],
                ),
                (
                    f"\tdef {req._function_name}(self):",
                    [
                        "\t\theaders = {}",
                        "\t\tcookies = {}",
                        f"\t\t{text_utils.REQUEST_VARIABLE_NAME} = requests.get('{GOOGLE}', headers=headers, cookies=cookies)",
                    ],
                ),
            ],
        )
        assert text_utils.generate_replacement(rreq) == text

    def test_generate_replacement_matching_string(self):
        pass

    def test_generate_replacement_matching_list(self):
        pass

    def test_generate_replacement_matching_list_element(self):
        pass
