from __future__ import annotations
from typing import Any, TYPE_CHECKING
import itertools
import asyncio
import json
import re
import httpx
import requests
from urllib import parse
from black import format_str, FileMode
from .constants import URL_REGEX, METHOD_REGEX, OPTS_REGEX, DATA_HANDLER


if TYPE_CHECKING:
    from models import _RequestifyObject, _RequestifyList


def format_url(url: str) -> str:
    url = url.strip("'").strip('"').rstrip('/')
    if not (
        url.startswith('//')
        or url.startswith('http://')
        or url.startswith('https://')
    ):
        url = 'https://' + url  # good enough

    return url


def find_url_or_error(s: str) -> str:
    might_include_url = re.search(URL_REGEX, s)
    if might_include_url:
        url = might_include_url.groups(0)[0]
    else:
        raise ValueError('Could not find a url')
    return url  # type: ignore


def find_method(s: str):
    return re.search(METHOD_REGEX, s)


# https://stackoverflow.com/questions/5389507/iterating-over-every-two-elements-in-a-list
def pairwise(iterable):
    """s -> (s0, s1), (s2, s3), (s4, s5), ..."""
    a = iter(iterable)
    return zip(a, a)


def uppercase_boolean_values(
    opts: list[tuple[str, str]]
) -> list[tuple[str, str]]:
    ret_opts = []
    for _, value in opts:
        if value.find('false') != -1:
            value = value.replace('false', 'False')
        if value.find('true') != -1:
            value = value.replace('true', 'True')
        ret_opts.append((_, value))

    return ret_opts


def flatten_list(l: list) -> list:
    return list(itertools.chain.from_iterable(l))


def find_opts(meta: str) -> list[str]:
    opts = re.findall(OPTS_REGEX, meta)
    flat_opts = flatten_list(opts)
    return [option for option in flat_opts if option]


# requests does not have support for flags such as --compressed, --resolve,
# so there's no way to convert
def _get_opts(meta: str) -> list[tuple[str, str]]:
    opts = find_opts(meta)
    assert len(opts) % 2 == 0, 'Request header(s) or flag(s) missing'
    return [
        (flag, data)
        for flag, data in pairwise(opts)
        if flag == '-H' or flag in DATA_HANDLER
    ]


def split_list(l: list[str]) -> list[str]:
    return list(
        itertools.chain.from_iterable([element.split(' ') for element in l])
    )


def get_response(requestify_object: _RequestifyObject) -> Any | str:
    try:
        response = asyncio.run(_get_response_async(requestify_object))
    except TimeoutError:
        print('Async call failed. Using synchronous requests instead')
        response = _get_response_requests(requestify_object)

    response_data = get_json_or_text(response)
    return response_data


def get_responses(requestify_list: _RequestifyList) -> list[Any]:
    try:
        responses = asyncio.run(_get_responses_async(requestify_list))
    except TimeoutError:
        print('Async call failed. Using synchronous requests instead')
        responses = _get_responses_requests(requestify_list)

    return [get_json_or_text(response) for response in responses]


async def _get_response_async(
    requestify_object: _RequestifyObject,
) -> httpx._models.Response:
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=requestify_object._method,
            url=requestify_object._url,
            data=requestify_object._data,
            headers=requestify_object._headers,
            cookies=requestify_object._cookies,
        )

    return response


async def _get_responses_async(
    requestify_list: _RequestifyList,
) -> tuple[httpx._models.Response] | list[Any]:
    async with httpx.AsyncClient() as client:
        request = (
            client.request(
                method=requestify_object._method,
                url=requestify_object._url,
                headers=requestify_object._headers,
                cookies=requestify_object._cookies,
            )
            for requestify_object in requestify_list
        )
        responses = await asyncio.gather(*request)

    return responses


def _get_response_requests(
    requestify_object: _RequestifyObject,
) -> requests.models.Response:
    response = requests.request(
        method=requestify_object._method,
        url=requestify_object._url,
        data=requestify_object._data,
        headers=requestify_object._headers,
        cookies=requestify_object._cookies,
    )

    return response


def _get_responses_requests(
    requestify_list: _RequestifyList,
) -> list[requests.models.Response]:
    return [
        _get_response_requests(requestify_object)
        for requestify_object in requestify_list
    ]


def get_json_or_text(
    request: requests.models.Response | httpx._models.Response,
) -> Any:
    response = ''
    try:
        response = request.json()
    except json.JSONDecodeError:
        response = request.text

    return response


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
    url_regex = re.compile(r'[^0-9a-zA-Z_]+')
    return re.sub(url_regex, '_', netloc)


def get_netloc(url: str) -> str:
    url_parts = parse.urlparse(url)

    if url_parts:
        netloc = url_parts.netloc
        if netloc:
            return beautify_netloc(netloc)
        raise ValueError('Not a valid netloc')

    raise ValueError('Not a valid url')
