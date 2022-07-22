from __future__ import annotations
from typing import Any
import httpx
import itertools
import asyncio
import requests
import json
import re
from black import format_str, FileMode
from urllib import parse

# name that will be used for class with requests
REQUESTS_CLASS_NAME = "RequestsTest"
RESPONSE_VARIABLE_NAME = "response"

# methods to be called if data flags are present
DATA_HANDLER = {
    "-d": lambda x: get_data_dict(x),
    "--data": lambda x: get_data_dict(x),
    "--data-ascii": lambda x: get_data_dict(x),
    "--data-binary": lambda x: bytes(x, encoding="utf-8"),
    "--data-raw": lambda x: get_data_dict(x),
    "--data-urlencode": lambda x: parse.quote(x),
}

METHOD_REGEX = re.compile(
    f'({"|".join(name for name in DATA_HANDLER)})|(?:-X)\s+(\S\w+\S)'
)
OPTS_REGEX = re.compile(
    """ (-{1,2}\S+)\s+?"([\S\s]+?)"|(-{1,2}\S+)\s+?'([\S\s]+?)'""", re.VERBOSE
)
URL_REGEX = re.compile(
    "((?:(?<=[^a-zA-Z0-9]){0,}(?:(?:https?\:\/\/){0,1}(?:[a-zA-Z0-9\%]{1,}\:[a-zA-Z0-9\%]{1,}[@]){,1})(?:(?:\w{1,}\.{1}){1,5}(?:(?:[a-zA-Z]){1,})|(?:[a-zA-Z]{1,}\/[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\:[0-9]{1,4}){1})){1}(?:(?:(?:\/{0,1}(?:[a-zA-Z0-9\-\_\=\-]){1,})*)(?:[?][a-zA-Z0-9\=\%\&\_\-]{1,}){0,1})(?:\.(?:[a-zA-Z0-9]){0,}){0,1})"
)


def format_url(url: str) -> str:
    url = url.strip("'").strip('"').rstrip("/")
    if not (
        url.startswith("//") or url.startswith("http://") or url.startswith("https://")
    ):
        url = "https://" + url  # good enough

    return url


def find_url_or_error(s: str) -> str:
    might_include_url = re.search(URL_REGEX, s)
    if might_include_url:
        url = might_include_url.groups(0)[0]
    else:
        raise ValueError("Could not find a url")
    return url  # type: ignore


def get_list_of_strings_without_url(list_of_strings: list[str], url: str) -> list[str]:
    return [s for s in list_of_strings if s != url]


# https://stackoverflow.com/questions/5389507/iterating-over-every-two-elements-in-a-list
def pairwise(iterable):
    "s -> (s0, s1), (s2, s3), (s4, s5), ..."
    a = iter(iterable)
    return zip(a, a)


def uppercase_boolean_values(opts: list[tuple[str, str]]) -> list[tuple[str, str]]:
    ret_opts = []
    for _, value in opts:
        if value.find("false") != -1:
            value = value.replace("false", "False")
        if value.find("true") != -1:
            value = value.replace("true", "True")
        ret_opts.append((_, value))

    return ret_opts


def find_and_get_opts(meta: str) -> list[str]:
    opts = re.findall(OPTS_REGEX, meta)
    _ = list(itertools.chain.from_iterable(opts))
    return [option for option in _ if option]


def split_and_flatten_list(l: list[str]) -> list[str]:
    return list(itertools.chain.from_iterable([element.split(" ") for element in l]))


def get_json_or_text(
    request: requests.models.Response | httpx._models.Response,
) -> Any:
    response = ""
    try:
        response = request.json()
    except json.JSONDecodeError:
        response = request.text

    return response


async def _get_response_async(
    requestify_object: RequestifyObject,
) -> httpx._models.Response:
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=requestify_object.method,
            url=requestify_object.url,
            data=requestify_object.data,
            headers=requestify_object.headers,
            cookies=requestify_object.cookies,
        )

    return response


async def _get_responses_async(
    requestify_list: list[RequestifyObject],
) -> tuple[httpx._models.Response]:
    async with httpx.AsyncClient() as client:
        request = (
            client.request(
                method=requestify_object.method,
                url=requestify_object.url,
                headers=requestify_object.headers,
                cookies=requestify_object.cookies,
            )
            for requestify_object in requestify_list
        )
        responses = await asyncio.gather(*request)

    return responses


def _get_response_requests(
    requestify_object: RequestifyObject,
) -> requests.models.Response:
    response = requests.request(
        method=requestify_object.method,
        url=requestify_object.url,
        data=requestify_object.data,
        headers=requestify_object.headers,
        cookies=requestify_object.cookies,
    )

    return response


def _get_responses_requests(
    requestify_list: list[RequestifyObject],
) -> list[requests.models.Response]:
    return [
        _get_response_requests(requestify_object)
        for requestify_object in requestify_list
    ]


def get_response(requestify_object: RequestifyObject) -> Any | str:
    try:
        response = asyncio.run(_get_response_async(requestify_object))
    except TimeoutError:
        print("Async call failed. Using synchronous requests instead")
        response = _get_response_requests(requestify_object)

    return get_json_or_text(response)


def get_responses(requestify_list: list[RequestifyObject]) -> list[Any]:
    try:
        responses = asyncio.run(_get_responses_async(requestify_list))
    except TimeoutError:
        print("Async call failed. Using synchronous requests instead")
        responses = _get_responses_requests(requestify_list)

    return [get_json_or_text(response) for response in responses]


# TODO: test this, improve comment
# Parses data if it's given in the url (application/x-www-form-urlencoded),
# or formats it if given in body
def get_data_dict(query: str) -> dict[str, str] | str:
    data = dict(parse.parse_qsl(query))
    alt = (
        query
        if query.startswith("'")
        else json.loads(query.replace("'", '"').strip('"'))
    )
    return data if data else alt


def beautify_string(string: str) -> str:
    return format_str(string, mode=FileMode())


def beautify_netloc(netloc: str) -> str:
    url_regex = re.compile(r"[^0-9a-zA-Z_]+")
    return re.sub(url_regex, "_", netloc)


def get_netloc(url: str) -> str:
    url_parts = parse.urlparse(url)

    if url_parts:
        netloc = url_parts.netloc
        if netloc:
            return beautify_netloc(netloc)
        else:
            raise ValueError("Not a valid netloc")

    else:
        raise ValueError("Not a valid url")


def is_valid_response(response: Any) -> bool:
    return isinstance(response, dict) or isinstance(response, list)


def is_list_of_jsons(list_to_test: list) -> bool:
    if not isinstance(list_to_test, list):
        return False
    for assumed_dict in list_to_test:
        if not isinstance(assumed_dict, dict):
            return False

    return True


def is_json(data: Any) -> bool:
    return is_list_of_jsons(data) or isinstance(data, dict)
