from typing import Any
import httpx
import asyncio
import requests
import json
import re
from black import format_str, FileMode
from urllib import parse

from requestify.requestify import RequestifyObject


def get_json_or_text(
    request: requests.models.Response | httpx._models.Response,
) -> Any | str:
    response = ""
    try:
        response = request.json()
    except json.JSONDecodeError:
        response = request.text

    return response


async def __get_response_async(
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


async def __get_responses_async(
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


def __get_response_requests(
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


def __get_responses_requests(
    requestify_list: list[RequestifyObject],
) -> list[requests.models.Response]:
    return [
        __get_response_requests(requestify_object)
        for requestify_object in requestify_list
    ]


def get_response(requestify_object: RequestifyObject) -> Any | str:
    try:
        response = asyncio.run(__get_response_async(requestify_object))
    except TimeoutError:
        print("Async call failed. Using synchronous requests instead")
        response = __get_response_requests(requestify_object)

    return get_json_or_text(response)


def get_responses(requestify_list: list[RequestifyObject]) -> list[Any | str]:
    try:
        responses = asyncio.run(__get_responses_async(requestify_list))
    except TimeoutError:
        print("Async call failed. Using synchronous requests instead")
        responses = __get_responses_requests(requestify_list)

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
