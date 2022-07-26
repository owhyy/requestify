from __future__ import annotations
from typing import Any

REQUEST_VARIABLE_NAME = "request"
REQUEST_CLASS_NAME = "RequestsTest"
REQUEST_MATCHING_DATA_DICT_NAME = "workflow"

FunctionTextType = tuple[str, list[str]]
ClassTextType = tuple[str, list[FunctionTextType]]

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
) -> FunctionTextType:
    name_part = f"""def {function_name}{"(self)" if is_in_class else "()"}:"""
    function_part = [*function_body]
    function_text = (name_part, function_part)
    return function_text


def __generate_indented_function(
    function_name: str, *function_body: str, is_in_class: bool
) -> FunctionTextType:
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
) -> FunctionTextType:
    return __generate_indented_function(function_name, *function_body, is_in_class=True)


def generate_function_text_outside_class(
    function_name: str, *function_body: str
) -> FunctionTextType:
    return __generate_indented_function(
        function_name, *function_body, is_in_class=False
    )


def __indent_function(function: FunctionTextType, indent_amount=1) -> FunctionTextType:
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

    indented_function = (indented_function_name, indented_function_body)
    return indented_function


def indent_function_inside_class(function: FunctionTextType) -> FunctionTextType:
    return __indent_function(function, indent_amount=2)


def indent_function_outside_class(
    function: FunctionTextType,
) -> FunctionTextType:
    return __indent_function(function)


"""
Class text
"""


def _generate_class_body(*functions: tuple[str, Any]) -> list[FunctionTextType]:
    class_body = []
    for function in functions:
        class_body.append(generate_function_text_inside_class(*function))
    return class_body


# generate class for tuple
# of function name and function body
def generate_class_text_from_ungenerated_functions(
    class_name: str, *class_functions: tuple[str, Any]
) -> ClassTextType:
    class_body = _generate_class_body(*class_functions)
    # indented_class_body = indent_class_body(*class_body)
    class_text = (f"class {class_name}():", class_body)
    return class_text


# generates class for functions that were already
# created with generate_function_text_* functions
def generate_class_text_from_generated_functions(
    class_name: str, *class_body: FunctionTextType
) -> ClassTextType:
    indented_class_body = indent_class_body(*class_body)
    class_text = (f"class {class_name}():", indented_class_body)
    return class_text


def indent_class_body(
    *class_body: FunctionTextType,
) -> list[FunctionTextType]:
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
) -> FunctionTextType:
    request_text = generate_requestify_base_text(req, with_headers, with_cookies)
    return generate_function_text_outside_class(req._function_name, *request_text)


def generate_requestify_class(
    req: _RequestifyObject, with_headers=True, with_cookies=True
) -> ClassTextType:
    request_text = generate_requestify_base_text(req, with_headers, with_cookies)
    return generate_class_text_from_ungenerated_functions(
        REQUEST_CLASS_NAME, (req._function_name, *request_text)
    )


def generate_requestify_list_function(
    rl: _RequestifyList, with_headers=True, with_cookies=True
) -> list[FunctionTextType]:
    request_functions = [
        generate_requestify_function(request, with_headers, with_cookies)
        for request in rl._requests
    ]
    return request_functions


def generate_requestify_list_class(
    rl: _RequestifyList, with_headers=True, with_cookies=True
) -> ClassTextType:
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


def generate_replacement(
    rreq: _ReplaceRequestify, with_headers=True, with_cookies=True
) -> ClassTextType:
    init_function = (
        "__init__",
        f"self.{REQUEST_MATCHING_DATA_DICT_NAME} = {rreq._function_names_and_their_responses}",
    )
    class_functions = [
        (
            request._function_name,
            *generate_requestify_base_text(request, with_headers, with_cookies),
        )
        for request in rreq._requests
    ]

    for request in rreq._matching_data:
        pass
    class_body = [init_function, class_functions]
    # return generate_class_text_from_ungenerated_functions(
    #     REQUEST_CLASS_NAME, *class_body
    # )
    # matching_data = rreq._matching_data
