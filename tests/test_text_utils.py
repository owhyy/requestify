import pytest
from requestify.models import _RequestifyObject, _RequestifyList, _ReplaceRequestify
from requestify.text_utils import (
    Function,
    FunctionBase,
    Class,
    generate_imports_text,
    generate_function_outside_class,
    generate_replacement,
    generate_class_function,
    _indent_function_inside_class,
    _indent_function_outside_class,
    generate_class,
    generate_requestify_base_text,
    REQUEST_VARIABLE_NAME,
    REQUEST_CLASS_NAME,
    REQUEST_MATCHING_DATA_DICT_NAME,
    generate_requestify_class,
    generate_requestify_list_class,
    generate_requestify_function,
    generate_requestify_list_function,
)
from .helpers import mock_get_responses

GOOGLE = "https://google.com"


@pytest.fixture
def unindented_function():
    return Function("def function_name():", ['print("i am a function body")'])


class TestBaseGeneration:
    def test_generate_imports(self):
        assert generate_imports_text("unittest", "numpy", "json") == [
            "import unittest",
            "import numpy",
            "import json",
        ]

    def test_generate_imports_no_args(self):
        assert len(generate_imports_text()) == 0

    def test_replace_function_name(self):
        pass

    def test_Function(self):
        expected = Function(
            "def function_name():",
            ["\tfoo = 10"],
        )
        actual = generate_function_outside_class(
            FunctionBase("function_name", ["foo = 10"])
        )
        assert actual.name == expected.name
        assert actual.body == expected.body

    def test_generate_function_text_inside_class(self):
        function_in_class = Function(
            "\tdef function_name(self):",
            [
                '\t\tprint("i am a function body")',
                '\t\tprint("this is another line")',
                "\t\tx=10",
            ],
        )
        assert (
            generate_class_function(
                FunctionBase(
                    "function_name",
                    [
                        'print("i am a function body")',
                        'print("this is another line")',
                        "x=10",
                    ],
                )
            )
            == function_in_class
        )

    def test_generate_function_text_outside_class(self):
        function_outside_class = Function(
            "def function_name():",
            [
                '\tprint("i am a function body")',
                '\tprint("this is another line")',
                "\tx=10",
            ],
        )
        assert (
            generate_function_outside_class(
                FunctionBase(
                    "function_name",
                    [
                        'print("i am a function body")',
                        'print("this is another line")',
                        "x=10",
                    ],
                )
            )
            == function_outside_class
        )

    def test_indent_function_inside_class(self, unindented_function):
        indented_function = Function(
            name="\tdef function_name():",
            body=['\t\tprint("i am a function body")'],
        )
        assert _indent_function_inside_class(unindented_function) == indented_function

    def test_indent_function_outside_class(self, unindented_function):
        indented_function = (
            "def function_name():",
            [
                '\tprint("i am a function body")',
            ],
        )
        assert _indent_function_outside_class(unindented_function) == indented_function

    def test_generate_class(self):
        base = FunctionBase(
            "foo",
            [
                'print("i am a function body")',
            ],
        )
        class_function = Function(
            "\tdef foo(self):",
            [
                '\t\tprint("i am a function body")',
            ],
        )
        assert generate_class("SomeClass", [base]) == Function(
            "class SomeClass():", [class_function]
        )


class TestModelTextGeneration(object):
    def test_request_variable_name_gets_set(self):
        req = _RequestifyObject(f"""curl -X post '{GOOGLE}' -H 'x: y'""")
        text = generate_requestify_base_text(req, True, True)
        request_text = text[3]
        assert REQUEST_VARIABLE_NAME in request_text

    def test_requestify_object_class_name_gets_set(self):
        req = _RequestifyObject(f"""curl -X post '{GOOGLE}' -H 'x: y'""")
        text = generate_requestify_class(req, True, True)
        assert REQUEST_CLASS_NAME in text.name

    def test_requestify_list_class_name_gets_set(self):
        rl = _RequestifyList(f"""curl -X post '{GOOGLE}' -H 'x: y'""")
        text = generate_requestify_list_class(rl, True, True)
        assert REQUEST_CLASS_NAME in text.name

    def test_requestify_object_function_name_gets_set(self):
        req = _RequestifyObject(f"""curl -X post '{GOOGLE}' -H 'x: y'""")
        text = generate_requestify_function(req, True, True)
        assert req._function_name in text.name

    def test_requestify_list_function_name_gets_set(self):
        req = _RequestifyList(f"""curl -X post '{GOOGLE}' -H 'x: y'""")
        text = generate_requestify_list_function(req, True, True)
        assert req._requests[0]._function_name in text[0].name

    def test_base_requstify_full(self):
        req = _RequestifyObject(
            f"""curl -X POST -H "x: y" -H "Cookie: span=eggs" -d '{{"bar": "foo"}}' {GOOGLE}"""
        )
        base_response_text = [
            "headers = {'x': 'y'}",
            "cookies = {'span': 'eggs'}",
            "data = {'bar': 'foo'}",
            f"{REQUEST_VARIABLE_NAME} = requests.{req._method}('{req._url}', headers=headers, cookies=cookies, data=data)",
        ]
        assert generate_requestify_base_text(req, True, True) == base_response_text

    def test_base_requestify_no_headers(self):
        req = _RequestifyObject(
            f"""curl -X POST -H "x: y" -H "Cookie: span=eggs" -d '{{"bar": "foo"}}' {GOOGLE}"""
        )
        base_response_text = [
            None,
            "cookies = {'span': 'eggs'}",
            "data = {'bar': 'foo'}",
            f"{REQUEST_VARIABLE_NAME} = requests.post('{GOOGLE}', cookies=cookies, data=data)",
        ]
        assert (
            generate_requestify_base_text(req, with_headers=False, with_cookies=True)
            == base_response_text
        )

    def test_base_requestify_no_data(self):
        req = _RequestifyObject(
            f"""curl -X POST -H "x: y" -H "Cookie: span=eggs" {GOOGLE}"""
        )
        base_response_text = [
            "headers = {'x': 'y'}",
            "cookies = {'span': 'eggs'}",
            None,
            f"{REQUEST_VARIABLE_NAME} = requests.{req._method}('{req._url}', headers=headers, cookies=cookies)",
        ]
        assert generate_requestify_base_text(req, True, True) == base_response_text

    def test_base_requestify_no_cookies(self):
        req = _RequestifyObject(
            f"""curl -X POST -H "x: y" -H "Cookie: span=eggs" -d '{{"bar": "foo"}}' {GOOGLE}"""
        )
        base_response_text = [
            "headers = {'x': 'y'}",
            None,
            "data = {'bar': 'foo'}",
            f"{REQUEST_VARIABLE_NAME} = requests.{req._method}('{req._url}', headers=headers, data=data)",
        ]
        assert generate_requestify_base_text(req, True, False) == base_response_text

    def test_base_requestify_no_headers_no_cookies(self):
        req = _RequestifyObject(
            f"""curl -X POST -H "x: y" -H "Cookie: span=eggs" -d '{{"bar": "foo"}}' {GOOGLE}"""
        )
        base_response_text = [
            None,
            None,
            "data = {'bar': 'foo'}",
            f"{REQUEST_VARIABLE_NAME} = requests.{req._method}('{req._url}', data=data)",
        ]
        assert generate_requestify_base_text(req, False, False) == base_response_text

    def test_base_requestify_no_data_no_cookies(self):
        req = _RequestifyObject(
            f"""curl -X POST -H "x: y" -H "Cookie: span=eggs" -d '{{"bar": "foo"}}' {GOOGLE}"""
        )
        base_response_text = [
            "headers = {'x': 'y'}",
            None,
            "data = {'bar': 'foo'}",
            f"{REQUEST_VARIABLE_NAME} = requests.{req._method}('{req._url}', headers=headers, data=data)",
        ]
        assert generate_requestify_base_text(req, True, False) == base_response_text

    def test_base_requestify_no_headers_no_data(self):
        req = _RequestifyObject(
            f"""curl -X POST -H "x: y" -H "Cookie: span=eggs" {GOOGLE}"""
        )
        base_response_text = [
            None,
            "cookies = {'span': 'eggs'}",
            None,
            f"{REQUEST_VARIABLE_NAME} = requests.{req._method}('{req._url}', cookies=cookies)",
        ]
        assert generate_requestify_base_text(req, False, True) == base_response_text

    def test_base_requestify_no_data_no_headers_no_cookies(self):
        req = _RequestifyObject(
            f"""curl -X POST -H "x: y" -H "Cookie: span=eggs" {GOOGLE}"""
        )
        base_response_text = [
            None,
            None,
            None,
            f"{REQUEST_VARIABLE_NAME} = requests.{req._method}('{req._url}')",
        ]
        assert generate_requestify_base_text(req, False, False) == base_response_text

    def test_generate_requestify_function(self):
        req = _RequestifyObject(f"curl -X GET '{GOOGLE}'")
        text = (
            f"def {req._function_name}():",
            [
                "\theaders = {}",
                "\tcookies = {}",
                f"\t{REQUEST_VARIABLE_NAME} = requests.get('{GOOGLE}', headers=headers, cookies=cookies)",
            ],
        )
        assert generate_requestify_function(req) == text

    def test_generate_requestify_class(self):
        req = _RequestifyObject(f"curl -X GET '{GOOGLE}")
        text = Class(
            f"class {REQUEST_CLASS_NAME}():",
            [
                Function(
                    f"\tdef {req._function_name}(self):",
                    [
                        "\t\theaders = {}",
                        "\t\tcookies = {}",
                        f"\t\t{REQUEST_VARIABLE_NAME} = requests.get('{GOOGLE}', headers=headers, cookies=cookies)",
                    ],
                )
            ],
        )
        assert generate_requestify_class(req) == text

    def test_generate_requestify_list_function(self):
        req = f"curl -X GET '{GOOGLE}"
        body = [
            "\theaders = {}",
            "\tcookies = {}",
            f"\t{REQUEST_VARIABLE_NAME} = requests.get('{GOOGLE}', headers=headers, cookies=cookies)",
        ]

        rl = _RequestifyList(req)
        reqs = rl._requests
        text = [
            Function(f"def {reqs[0]._function_name}():", body),
        ]

        assert generate_requestify_list_function(rl) == text

    def test_generate_requestify_list_class(self):
        req = f"curl -X GET '{GOOGLE}"
        rl = _RequestifyList(req)
        req = rl._requests
        text = Class(
            f"class {REQUEST_CLASS_NAME}():",
            [
                Function(
                    f"\tdef {req[0]._function_name}(self):",
                    [
                        "\t\theaders = {}",
                        "\t\tcookies = {}",
                        f"\t\t{REQUEST_VARIABLE_NAME} = requests.get('{GOOGLE}', headers=headers, cookies=cookies)",
                    ],
                )
            ],
        )
        assert generate_requestify_list_class(rl) == text

    def test_generate_replacement_no_matching_data(self, mocker):
        mock_get_responses(mocker)
        rreq = _ReplaceRequestify(f"curl -X GET '{GOOGLE}")
        req = rreq._requests[0]
        text = Class(
            name=f"class {REQUEST_CLASS_NAME}():",
            body=[
                Function(
                    ("\tdef __init__(self):"),
                    [f"\t\tself.{REQUEST_MATCHING_DATA_DICT_NAME} = {{}}"],
                ),
                Function(
                    f"\tdef {req._function_name}(self):",
                    [
                        "\t\theaders = {}",
                        "\t\tcookies = {}",
                        f"\t\t{REQUEST_VARIABLE_NAME} = requests.get('{GOOGLE}', headers=headers, cookies=cookies)",
                        f"\t\tself.{REQUEST_MATCHING_DATA_DICT_NAME}['{req._function_name}'] = {REQUEST_VARIABLE_NAME}",
                    ],
                ),
            ],
        )
        assert generate_replacement(rreq) == text

    def test_generate_replacement_matching_dict(self, mocker):
        mocker.patch(
            "requestify.models.utils.get_responses",
            #               GET       POST
            return_value=[{"foo": 1}, None],
        )
        curl1 = f"curl -X GET {GOOGLE}"
        curl2 = f"""curl -X POST -d '{{"bar": 1, "span": "eggs"}}' {GOOGLE}"""
        rreq = _ReplaceRequestify(curl1, curl2)
        r1, r2 = rreq._requests

        text = Class(
            name=f"class {REQUEST_CLASS_NAME}():",
            body=[
                Function(
                    ("\tdef __init__(self):"),
                    [f"\t\tself.{REQUEST_MATCHING_DATA_DICT_NAME} = {{}}"],
                ),
                Function(
                    f"\tdef {r1._function_name}(self):",
                    [
                        "\t\theaders = {}",
                        "\t\tcookies = {}",
                        f"\t\t{REQUEST_VARIABLE_NAME} = requests.get('{GOOGLE}', headers=headers, cookies=cookies)",
                        f"\t\tself.{REQUEST_MATCHING_DATA_DICT_NAME}['{r1._function_name}'] = {REQUEST_VARIABLE_NAME}",
                    ],
                ),
                Function(
                    f"\tdef {r2._function_name}(self):",
                    [
                        "\t\theaders = {}",
                        "\t\tcookies = {}",
                        f"""\t\tdata = {{'bar': self.{REQUEST_MATCHING_DATA_DICT_NAME}['{r1._function_name}']['foo'], 'span': 'eggs'}}""",
                        f"\t\t{REQUEST_VARIABLE_NAME} = requests.post('{GOOGLE}', headers=headers, cookies=cookies, data=data)",
                        f"\t\tself.{REQUEST_MATCHING_DATA_DICT_NAME}['{r2._function_name}'] = {REQUEST_VARIABLE_NAME}",
                    ],
                ),
            ],
        )
        assert generate_replacement(rreq) == text

    def test_generate_replacement_matching_list_element(self, mocker):
        mocker.patch(
            "requestify.models.utils.get_responses",
            return_value=[
                [{"span": 5}, [{"xyz": 10}, {"baz": 34}, [{"eggs": 2}]]],
                None,
            ],
        )
        curl1 = f"curl -X GET {GOOGLE}"
        curl2 = f"""curl -X POST -d '{{"span": 34, "eggs": 2}}' {GOOGLE}"""
        rreq = _ReplaceRequestify(curl1, curl2)
        r1, r2 = rreq._requests

        text = Class(
            name=f"class {REQUEST_CLASS_NAME}():",
            body=[
                Function(
                    ("\tdef __init__(self):"),
                    [f"\t\tself.{REQUEST_MATCHING_DATA_DICT_NAME} = {{}}"],
                ),
                Function(
                    f"\tdef {r1._function_name}(self):",
                    [
                        "\t\theaders = {}",
                        "\t\tcookies = {}",
                        f"\t\t{REQUEST_VARIABLE_NAME} = requests.get('{GOOGLE}', headers=headers, cookies=cookies)",
                        f"\t\tself.{REQUEST_MATCHING_DATA_DICT_NAME}['{r1._function_name}'] = {REQUEST_VARIABLE_NAME}",
                    ],
                ),
                Function(
                    f"\tdef {r2._function_name}(self):",
                    [
                        "\t\theaders = {}",
                        "\t\tcookies = {}",
                        f"""\t\tdata = {{'span': self.{REQUEST_MATCHING_DATA_DICT_NAME}['{r1._function_name}'][1][1]['baz'], 'eggs': self.{REQUEST_MATCHING_DATA_DICT_NAME}['{r1._function_name}'][1][2][0]['eggs']}}""",
                        f"\t\t{REQUEST_VARIABLE_NAME} = requests.post('{GOOGLE}', headers=headers, cookies=cookies, data=data)",
                        f"\t\tself.{REQUEST_MATCHING_DATA_DICT_NAME}['{r2._function_name}'] = {REQUEST_VARIABLE_NAME}",
                    ],
                ),
            ],
        )
        assert generate_replacement(rreq) == text

    def test_generate_replacement_headers(self, mocker):
        mocker.patch(
            "requestify.models.utils.get_responses",
            return_value=[{"foo": "1"}, None],
        )
        curl1 = f"curl -X GET {GOOGLE}"
        curl2 = f"curl -X GET {GOOGLE} -H 'bar: 1'"
        rreq = _ReplaceRequestify(curl1, curl2)
        r1, r2 = rreq._requests

        text = Class(
            name=f"class {REQUEST_CLASS_NAME}():",
            body=[
                Function(
                    ("\tdef __init__(self):"),
                    [f"\t\tself.{REQUEST_MATCHING_DATA_DICT_NAME} = {{}}"],
                ),
                Function(
                    f"\tdef {r1._function_name}(self):",
                    [
                        "\t\theaders = {}",
                        "\t\tcookies = {}",
                        f"\t\t{REQUEST_VARIABLE_NAME} = requests.get('{GOOGLE}', headers=headers, cookies=cookies)",
                        f"\t\tself.{REQUEST_MATCHING_DATA_DICT_NAME}['{r1._function_name}'] = {REQUEST_VARIABLE_NAME}",
                    ],
                ),
                Function(
                    f"\tdef {r2._function_name}(self):",
                    [
                        f"""\t\theaders = {{'bar': self.{REQUEST_MATCHING_DATA_DICT_NAME}['{r1._function_name}']['foo']}}""",
                        "\t\tcookies = {}",
                        f"\t\t{REQUEST_VARIABLE_NAME} = requests.get('{GOOGLE}', headers=headers, cookies=cookies)",
                        f"\t\tself.{REQUEST_MATCHING_DATA_DICT_NAME}['{r2._function_name}'] = {REQUEST_VARIABLE_NAME}",
                    ],
                ),
            ],
        )
        assert generate_replacement(rreq) == text
