from __future__ import annotations
from collections import namedtuple
from typing import TYPE_CHECKING
from .constants import (
    REQUEST_VARIABLE_NAME,
    REQUEST_CLASS_NAME,
    REQUEST_MATCHING_DATA_DICT_NAME,
)

if TYPE_CHECKING:
    from models import (
        _RequestifyObject,
        _RequestifyList,
        _ReplaceRequestify,
        RequestMatch,
    )


"""
name is the name of the function, body is function body
"""
FunctionBase = namedtuple("FunctionBase", "name body")

"""
name is `def name(self):` or `def name()`,
where name is FunctionBase.name.
body is FunctionBase.body, but indented
"""
Function = namedtuple("Function", "name body")

"""
name is REQUEST_CLASS_NAME, body is a list of `Function` objects
"""
Class = namedtuple("Class", "name body")


"""
General
"""


def generate_imports_text(*packages: str) -> list[str]:
    return [f"import {package}" for package in packages]


"""
Functions
"""


def generate_function_text(function: Function) -> str:
    return function.name + "".join(function.body).replace('"', '`').replace('`', '')


def generate_class_function(base: FunctionBase) -> Function:
    return _generate_indented_function(base, is_in_class=True)


def generate_function_outside_class(base: FunctionBase) -> Function:
    return _generate_indented_function(base, is_in_class=False)


def _generate_indented_function(base: FunctionBase, is_in_class: bool) -> Function:
    function_text = _generate_unindented_function(base, is_in_class=is_in_class)
    indented_function = (
        _indent_function_inside_class(function_text)
        if is_in_class
        else _indent_function_outside_class(function_text)
    )
    return indented_function


def _generate_unindented_function(base: FunctionBase, is_in_class: bool) -> Function:
    name_part = f"""def {base.name}{"(self)" if is_in_class else "()"}:"""
    function_part = base.body
    function_text = Function(name=name_part, body=function_part)
    return function_text


def _indent_function_inside_class(function: Function) -> Function:
    return _indent_function(function, indent_amount=2)


def _indent_function_outside_class(
    function: Function,
) -> Function:
    return _indent_function(function, indent_amount=1)


def _indent_function(function: Function, indent_amount) -> Function:
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

    indented_function_name = first_line_indent + function.name
    indented_function_body = [body_indent + line for line in function.body if line]

    indented_function = Function(indented_function_name, indented_function_body)
    return indented_function


"""
Class
"""


def generate_class_text(class_tuple: Class) -> str:
    functions = [generate_function_text(function) for function in class_tuple.body]
    return class_tuple.name + "".join(functions)


# generates class for functions that were already
# created with generate_function_text_* functions
def generate_class(class_name: str, class_body: list[FunctionBase]) -> Class:
    class_functions = [generate_class_function(function) for function in class_body]
    c = Class(f"class {class_name}():", class_functions)
    return c


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
    else:
        requestify_text.append(None)

    if with_cookies:
        requestify_text.append(f"cookies = {req._cookies}")
        request_options += ", cookies=cookies"
    else:
        requestify_text.append(None)

    if req._data:
        requestify_text.append(f"data = {req._data}")
        request_options += ", data=data"
    else:
        requestify_text.append(None)

    requestify_text.append(
        f"{REQUEST_VARIABLE_NAME} = requests.{req._method}('{req._url}'{request_options})"
    )
    return requestify_text


def generate_replacement_base_text(
    req: _RequestifyObject, with_headers=True, with_cookies=True
) -> list[str]:
    body = generate_requestify_base_text(req, with_headers, with_cookies)
    assignment_to_data_dict = f"self.{REQUEST_MATCHING_DATA_DICT_NAME}['{req._function_name}'] = {REQUEST_VARIABLE_NAME}"
    body.append(assignment_to_data_dict)
    return body


def generate_requestify_function(
    req: _RequestifyObject, with_headers=True, with_cookies=True
) -> Function:
    request_text = generate_requestify_base_text(req, with_headers, with_cookies)
    return generate_function_outside_class(
        FunctionBase(req._function_name, request_text)
    )


def generate_requestify_class(
    req: _RequestifyObject, with_headers=True, with_cookies=True
) -> Class:
    function_body = generate_requestify_base_text(req, with_headers, with_cookies)
    return generate_class(
        REQUEST_CLASS_NAME, [FunctionBase(req._function_name, function_body)]
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
        FunctionBase(
            request._function_name,
            generate_requestify_base_text(request, with_headers, with_cookies),
        )
        for request in rl._requests
    ]
    return generate_class(REQUEST_CLASS_NAME, class_body)


def generate_replacement(
    rreq: _ReplaceRequestify, with_headers=True, with_cookies=True
) -> Class:
    init_function = FunctionBase(
        "__init__",
        [f"self.{REQUEST_MATCHING_DATA_DICT_NAME} = {{}}"],
    )

    class_body = [init_function]

    for request in rreq._requests:
        body = generate_replacement_base_text(request, with_headers, with_cookies)
        function = FunctionBase(request._function_name, body)
        class_body.append(function)

    return generate_class(REQUEST_CLASS_NAME, class_body)
