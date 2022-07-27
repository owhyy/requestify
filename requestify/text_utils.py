from __future__ import annotations
from collections import namedtuple
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from models import _RequestifyObject, _RequestifyList, _ReplaceRequestify

REQUEST_VARIABLE_NAME = "request"
REQUEST_CLASS_NAME = "RequestsTest"
REQUEST_MATCHING_DATA_DICT_NAME = "workflow"

Function = namedtuple("Function", "name body")
Class = namedtuple("Class", "name body")

"""
General
"""


def generate_imports_text(*packages: str) -> list[str]:
    return [f"import {package}" for package in packages]


"""
Function text
"""


def __generate_function_text(
    function_name: str, *function_body: str, is_in_class: bool
) -> Function:
    name_part = f"""def {function_name}{"(self)" if is_in_class else "()"}:"""
    function_part = [*function_body]
    function_text = Function(name=name_part, body=function_part)
    return function_text


def __generate_indented_function(
    function_name: str, *function_body: str, is_in_class: bool
) -> Function:
    function_text = __generate_function_text(
        function_name, *function_body, is_in_class=is_in_class
    )
    indented_function = (
        indent_function_inside_class(function_text)
        if is_in_class
        else indent_function_outside_class(function_text)
    )
    return indented_function


def generate_function_text_inside_class(
    function_name: str, *function_body: str
) -> Function:
    return __generate_indented_function(function_name, *function_body, is_in_class=True)


def generate_function_text_outside_class(
    function_name: str, *function_body: str
) -> Function:
    return __generate_indented_function(
        function_name, *function_body, is_in_class=False
    )


def __indent_function(function: Function, indent_amount=1) -> Function:
    """
    Indent levels means indent level for body, not for first line.
    Therefore, a indent level of 1 looks like
    def fun()
        pass
    ^^^^
    """
    first_line_indent_amount = indent_amount - 1 if indent_amount > 0 else indent_amount
    first_line_indent = "\t" * first_line_indent_amount
    body_indent = "\t" * indent_amount

    function_name = function[0]
    indented_function_name = first_line_indent + function_name

    indented_function_body = []
    function_body = function[1]
    for line in function_body:
        indented_function_body.append(body_indent + line)

    indented_function = Function(indented_function_name, indented_function_body)
    return indented_function


def indent_function_inside_class(function: Function) -> Function:
    return __indent_function(function, indent_amount=2)


def indent_function_outside_class(
    function: Function,
) -> Function:
    return __indent_function(function)


"""
Class text
"""


def _generate_class_body(*functions: tuple[str, Any]) -> list[Function]:
    class_body = []
    for function in functions:
        class_body.append(generate_function_text_inside_class(*function))
    return class_body


# generate class for tuple
# of function name and function body
def generate_class_text_from_ungenerated_functions(
    class_name: str, *class_functions: tuple[str, Any]
) -> Class:
    class_body = _generate_class_body(*class_functions)
    # indented_class_body = indent_class_body(*class_body)
    class_text = Class(f"class {class_name}():", class_body)
    return class_text


# generates class for functions that were already
# created with generate_function_text_* functions
def generate_class_text_from_generated_functions(
    class_name: str, *class_body: Function
) -> Class:
    indented_class_body = indent_class_body(*class_body)
    class_text = Class(f"class {class_name}():", indented_class_body)
    return class_text


def indent_class_body(
    *class_body: Function,
) -> list[Function]:
    indented_class_body = [
        indent_function_inside_class(function) for function in class_body
    ]
    return indented_class_body


"""
Requestify text
"""


def generate_requestify_base_text(
    req: _RequestifyObject, with_headers=True, with_cookies=True
) -> list[str]:
    requestify_text = []
    request_options = ""
    RequestFunction = namedtuple("RequestFunction", "headers cookies data")

    if with_headers:
        requestify_text.append(f"headers = {req._headers}")
        request_options += ", headers=headers"

    if with_cookies:
        requestify_text.append(f"cookies = {req._cookies}")
        request_options += ", cookies=cookies"

    if req._data:
        requestify_text.append(f"data = {req._data}")
        request_options += ", data=data"

    requestify_text.append(
        f"{REQUEST_VARIABLE_NAME} = requests.{req._method}('{req._url}'{request_options})"
    )
    return requestify_text


def generate_requestify_function(
    req: _RequestifyObject, with_headers=True, with_cookies=True
) -> Function:
    request_text = generate_requestify_base_text(req, with_headers, with_cookies)
    return generate_function_text_outside_class(req._function_name, *request_text)


def generate_requestify_class(
    req: _RequestifyObject, with_headers=True, with_cookies=True
) -> Class:
    request_text = generate_requestify_base_text(req, with_headers, with_cookies)
    return generate_class_text_from_ungenerated_functions(
        REQUEST_CLASS_NAME, (req._function_name, *request_text)
    )


def generate_requestify_list_function(
    rl: _RequestifyList, with_headers=True, with_cookies=True
) -> list[Function]:
    request_functions = [
        generate_requestify_function(request, with_headers, with_cookies)
        for request in rl._requests
    ]
    return request_functions


def generate_requestify_list_class(
    rl: _RequestifyList, with_headers=True, with_cookies=True
) -> Class:
    class_body = [
        (
            request._function_name,
            *generate_requestify_base_text(request, with_headers, with_cookies),
        )
        for request in rl._requests
    ]
    return generate_class_text_from_ungenerated_functions(
        REQUEST_CLASS_NAME, *class_body
    )


# TODO: determine index if with_headers and with_cookies is false
def generate_replacement(
    rreq: _ReplaceRequestify, with_headers=True, with_cookies=True
) -> Class:
    init_function = (
        "__init__",
        f"self.{REQUEST_MATCHING_DATA_DICT_NAME} = {rreq._requests_and_their_responses}",
    )
    class_functions = generate_requestify_list_function(rreq._requests)
    return None

    # for (
    #     current_request,
    #     current_field,
    #     matching_request,
    #     matching_field,
    # ) in rreq._matching_data.items():
    #     function_body = generate_requestify_base_text(
    #         current_request, with_headers, with_cookies
    #     )
    #     new_data_assignment = f"{REQUEST_MATCHING_DATA_DICT_NAME}[{matching_request._function_name}][{matching_request._index}]"
    #     class_functions[
    #         class_functions.index(current_request)
    #     ].body.data_assignment = new_data_assignment
    #
    # class_body = [init_function, class_functions]
    # return generate_class_text_from_ungenerated_functions(
    #     REQUEST_CLASS_NAME, *class_body
    # )
