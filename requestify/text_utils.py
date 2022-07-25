from __future__ import annotations
REQUEST_VARIABLE_NAME = "request"

FunctionTextType = tuple[str, list[str]]

"""
General
"""


def generate_imports_text(*packages: str) -> list[str]:
    return [f"import {package}" for package in packages]


"""
Requestify text
"""


def generate_requestify_base_text(
    req: RequestifyObject, with_headers=True, with_cookies=True
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
    req: RequestifyObject, with_headers=True, with_cookies=True
) -> FunctionTextType | None:
    request_text = generate_requestify_base_text(req, with_headers, with_cookies)
    return generate_function_text_outside_class(req._function_name, *request_text)


"""
Function text
"""


def __generate_function_text(
    function_name: str, *function_body: str, is_in_class: bool
) -> FunctionTextType | None:
    function_text = None

    if function_body:
        function_part = [*function_body]

        name_part = f"""def {function_name}{"(self)" if is_in_class else "()"}:"""
        function_text = (name_part, function_part)

    return function_text


def __generate_indented_function(
    function_name: str, *function_body: str, is_in_class: bool
) -> FunctionTextType | None:
    function_text = __generate_function_text(
        function_name, *function_body, is_in_class=is_in_class
    )

    if function_text:
        indented_function = (
            indent_function_inside_class(function_text)
            if is_in_class
            else indent_function_outside_class(function_text)
        )

    else:
        indented_function = None
    return indented_function


def generate_function_text_inside_class(
    function_name: str, *function_body: str
) -> FunctionTextType | None:
    return __generate_indented_function(function_name, *function_body, is_in_class=True)


def generate_function_text_outside_class(
    function_name: str, *function_body: str
) -> FunctionTextType | None:
    return __generate_indented_function(
        function_name, *function_body, is_in_class=False
    )


def __indent_function(
    function: FunctionTextType, indent_amount=1
) -> FunctionTextType | None:
    """
    Indent levels means indent level for body, not for first line.
    Therefore, a indent level of 1 looks like
    def fun()
        pass
    ^^^^
    """
    if function:
        first_line_indent_amount = (
            indent_amount - 1 if indent_amount > 0 else indent_amount
        )
        first_line_indent = "\t" * first_line_indent_amount
        body_indent = "\t" * indent_amount

        function_name = function[0]
        indented_function_name = first_line_indent + function_name

        indented_function_body = []
        function_body = function[1]
        for line in function_body:
            indented_function_body.append(body_indent + line)

        indented_function = (indented_function_name, indented_function_body)
    else:
        indented_function = None

    return indented_function


def indent_function_inside_class(
    function: FunctionTextType
) -> FunctionTextType | None:
    return __indent_function(function, indent_amount=2)


def indent_function_outside_class(
    function: FunctionTextType
) -> FunctionTextType | None:
    return __indent_function(function)


"""
Class text
"""


def generate_class_text(
        class_name: str, *class_body: FunctionTextType | None
) -> tuple[str, list[FunctionTextType | None]]:
    indented_class_body = indent_class_body(class_body) # type: list[FunctionTextType | None]
    class_text = (f"class {class_name}():", indented_class_body)

    return class_text


def indent_class_body(
    class_body: list[FunctionTextType]
) -> list[FunctionTextType | None]:
    indented_class_body = [
        indent_function_inside_class(function) for function in class_body
    ]
    return indented_class_body
