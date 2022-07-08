import requestify.text_utils as text_utils
import pytest


@pytest.fixture
def unindented_function():
    return ("def function_name():", ['print("i am a function body")'])


class TestTextUtils:
    def test_generate_imports(self):
        assert text_utils.generate_imports_text("unittest", "numpy", "json") == [
            "import unittest",
            "import numpy",
            "import json",
        ]

    def test_generate_imports_no_args(self):
        assert len(text_utils.generate_imports_text()) == 0

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

    def test_generate_function_text_no_body(self):
        assert (
            text_utils.generate_function_text_inside_class(
                function_name="function_without_body"
            )
            is None
        )

        assert (
            text_utils.generate_function_text_outside_class(
                function_name="function_without_body"
            )
            is None
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

    def test_indent_empty_function(self):
        assert (text_utils.indent_function_inside_class([])) is None
        assert (text_utils.indent_function_outside_class([])) is None

    def test_indent_class_body(self):
        unindented_class_function = (
            "define function_name(self):",
            [
                'print("i am a function body")',
            ],
        )

        indented_class_function = (
            "\tdefine function_name(self):",
            [
                '\t\tprint("i am a function body")',
            ],
        )
        unindented_class_body = [unindented_class_function] * 3
        indented_class_body = [indented_class_function] * 3

        assert (
            text_utils.indent_class_body(unindented_class_body) == indented_class_body
        )

    def test_generate_class_text(self):
        unindented_class_function = (
            "define function_name(self):",
            [
                'print("i am a function body")',
            ],
        )
        indented_class_function = (
            "\tdefine function_name(self):",
            [
                '\t\tprint("i am a function body")',
            ],
        )
        assert text_utils.generate_class_text(
            "SomeClass", unindented_class_function, unindented_class_function
        ) == ("class SomeClass():", [indented_class_function, indented_class_function])
