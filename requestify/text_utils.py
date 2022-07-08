"""
General
"""


from argparse import ArgumentTypeError


def generate_imports_text(*packages):
    return [f"import {package}" for package in packages]


"""
Function text
"""


def __generate_function_text(function_name, *function_body, is_in_class):
    function_text = None

    if function_body:
        function_part = [*function_body]

        name_part = f"""def {function_name}{"(self)" if is_in_class else "()"}:"""
        function_text = (name_part, function_part)

    return function_text


def __generate_indented_function(function_name, *function_body, is_in_class):
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


def generate_function_text_inside_class(function_name, *function_body):
    return __generate_indented_function(function_name, *function_body, is_in_class=True)


def generate_function_text_outside_class(function_name, *function_body):
    return __generate_indented_function(
        function_name, *function_body, is_in_class=False
    )


def __indent_function(function, indent_amount=1):
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


def indent_function_inside_class(function_as_list):
    return __indent_function(function_as_list, indent_amount=2)


def indent_function_outside_class(function_as_list):
    return __indent_function(function_as_list)


"""
Class text
"""


def generate_class_text(class_name, *class_body):
    indented_class_body = indent_class_body(class_body)
    class_text = (f"class {class_name}():", indented_class_body)

    return class_text


def indent_class_body(class_body):
    indented_class_body = [
        indent_function_inside_class(function) for function in class_body
    ]
    return indented_class_body
