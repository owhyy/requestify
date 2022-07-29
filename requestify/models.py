# from dataclasses import dataclass, field
import dataclasses
import re
from typing import Any
from collections import defaultdict
from requestify import utils
from .constants import DATA_HANDLER


class _RequestifyObject(object):
    def __str__(self):
        return self._function_name

    def __repr__(self):
        return f"RequestifyObject({self._base_string})"

    def __key(self):
        return (
            self._base_string,
            self._url,
            self._method,
            self._function_name,
        )

    def __hash__(self):
        return hash(self.__key())

    # TODO: test this
    def __eq__(self, other):
        if isinstance(other, _RequestifyObject):
            return (
                self.__key() == other.__key()
                # cookies and data are unhashable, but they also need to match when
                # checking for equality
                and self._cookies == other._cookies
                and self._data == other._data
            )
        return NotImplemented

    def __init__(self, base_string: str) -> None:
        self._base_string = " ".join(base_string.replace("\\", "").split())
        self._url = ""
        self._method = "get"
        self._headers = {}
        self._cookies = {}
        self._data: RequestDataType = dict()

        self._function_name = ""
        self._generate()

    def _generate(self) -> None:
        meta = self._base_string.split(" ", 2)
        assert len(meta) > 1, "No URL provided"
        assert meta[0] == "curl", "Not a valid cURL request"

        if len(meta) == 2:
            url = meta[1]
            self._initialize_curl_and_url_only(url)
        else:
            self._initialize_complete_request(" ".join(meta[1:]))

        self._set_function_name()

    def _initialize_curl_and_url_only(self, url: str) -> None:
        if re.search(utils.URL_REGEX, url):
            self._url = url
            self._method = "get"
        else:
            raise ValueError("Request method not specified, and is not a GET")

    def _initialize_complete_request(self, meta: str) -> None:
        self._set_url(meta)
        self._set_method(meta)
        self._set_opts(meta)

    def _set_url(self, meta: str) -> None:
        self._url = utils.format_url(utils.find_url_or_error(meta))

    def _set_method(self, meta: str) -> None:
        found = utils.find_method(meta)
        if found:
            dataflag, method = found.groups()

            if dataflag:
                if self._method == "get":
                    self._method = "post"
            elif method:
                self._method = method.strip("'").strip('"').lower()
        else:
            pass
            # raise

    def _set_opts(self, meta: str) -> None:
        opts = self._get_opts(meta)
        opts = utils.uppercase_boolean_values(opts)
        self._set_body(opts)

        headers = [option[1] for option in opts if option[0] == "-H"]
        self._set_headers(headers)

    # requests does not have support for flags such as --compressed, --resolve,
    # so there's no way to convert
    def _get_opts(self, meta: str) -> list[tuple[str, str]]:
        opts = utils.find_and_get_opts(meta)
        assert len(opts) % 2 == 0, "Request header(s) or flag(s) missing"
        return [
            (flag, data)
            for flag, data in utils.pairwise(opts)
            if flag == "-H" or flag in DATA_HANDLER
        ]

    def _set_body(self, opts: list[tuple[str, str]]) -> None:
        for option in opts:
            for flag, value in utils.pairwise(option):
                if flag in DATA_HANDLER:
                    self._data = DATA_HANDLER[flag](value)

    def _set_headers(self, headers: list[str]) -> None:
        for header in headers:
            try:
                k, v = header.split(": ", 1)
            except ValueError:
                print(f"invalid data: {header}")
                raise

            if k.lower() == "cookie":
                self._set_cookie(v)
            else:
                self._headers[k] = v

    def _set_cookie(self, text: str) -> None:
        cookies = text.split("; ")
        for cookie in cookies:
            try:
                k, v = cookie.split("=", 1)
                self._cookies[k] = v
            except ValueError:
                raise

    def _set_function_name(self) -> None:
        netloc = utils.get_netloc(self._url)
        function_name = f"{self._method}_{netloc}"
        self._function_name = function_name

    # def __write_to_file(self, file, with_headers=True, with_cookies=True):
    #     request = self.create_beautiful_response(with_headers, with_cookies)
    #     with open(file, "w") as f:
    #         f.write("\n".join(request) + "\n")
    #
    # def __write_to_stdio(self, with_headers=True, with_cookies=True):
    #     request = self.create_beautiful_response(with_headers, with_cookies)
    #     print(request)
    #
    # def to_file(self, filename, with_headers=True, with_cookies=True):
    #     self.__write_to_file(
    #         filename, with_headers=with_headers, with_cookies=with_cookies
    #     )
    #
    # def to_screen(self, with_headers=True, with_cookies=True):
    #     self.__write_to_stdio(with_headers, with_cookies)
    #
    # def execute(self):
    #     request = requests.request(
    #         method=self.method, url=self.url, headers=self.headers, cookies=self.cookies
    #     )
    #
    #     return utils.get_json_or_text(request)
    #


class _RequestifyList(object):
    def __init__(self, *curls: str):
        self._base_list = curls
        self._requests: list[_RequestifyObject] = []
        self._existing_function_names = defaultdict(int)
        self._generate()

    def __len__(self):
        return len(self._requests)

    def __iter__(self):
        for request in self._requests:
            yield request

    def __getitem__(self, index):
        return self._requests[index]

    def __str__(self):
        return f"RequestifyList{[request.__str__() for request in self._requests]}"

    def __repr__(self):
        return f"RequestifyList{[request.__repr__() for request in self._requests]}"

    def _generate(self) -> None:
        for curl in self._base_list:
            request = _RequestifyObject(curl)
            self._requests.append(request)

        self._set_function_names()

    def _set_function_names(self) -> None:
        for request in self._requests:
            base_function_name = request._function_name
            function_count = self._existing_function_names[base_function_name]
            function_name = f"{base_function_name}{('_' + str(function_count) if function_count else '')}"
            request._function_name = (
                function_name if function_name else base_function_name
            )
            self._existing_function_names[base_function_name] += 1


RequestDataType = dict[str, Any]
ResponseDataType = dict[str, RequestDataType | list[RequestDataType]]


@dataclasses.dataclass
class RequestMatch:
    request: _RequestifyObject
    field: str
    matching_request: _RequestifyObject
    request_field: str
    value: Any
    indices_of_match: list[int] = dataclasses.field(default_factory=list)


class _ReplaceRequestify:
    def __init__(self, *curls):
        self._requests = _RequestifyList(*curls)

        # requests and data they produced
        self._requests_and_their_responses: dict[
            _RequestifyObject, ResponseDataType
        ] = {}
        self._matching_data: list[RequestMatch] = []
        # self._matching_headers: dict[str, dict[str, tuple[str, str]]] = {}
        # self._matching_url_content: dict[str, dict[str, tuple[str, str]]] = {}
        self._map_requests_to_responses()
        self._initialize_matching_data()
        # self._initialize_matching_headers()
        # self._initialize_matching_url_values()

    def _map_requests_to_responses(self) -> None:
        assert len(self._requests) > 0, "There must be at least one request"
        responses = utils.get_responses(self._requests)
        for request, response in zip(self._requests, responses):
            self._requests_and_their_responses[request] = response

    def _initialize_matching_data(self) -> None:
        for current_request in self._requests:
            self._match(current_request)

    def _match(self, current_request):
        request_body = current_request._data

        for current_field, current_value in request_body.items():
            matching_field, indices = self._get_matching_field_and_indices(
                current_request, current_value
            ) or (None, [])
            matching_request = self._get_matching_request(
                current_request, current_value
            )
            if matching_field and matching_request:
                match = RequestMatch(
                    current_request,
                    current_field,
                    matching_request,
                    matching_field,
                    current_value,
                    indices,
                )
                self._matching_data.append(match)

    @staticmethod
    def _get_key_and_index_where_values_match(
        value: Any, d: list[dict] | dict, indices=None
    ) -> tuple[Any, list[int]] | None:
        indices = indices or []
        if isinstance(d, dict):
            for response_field, response_value in d.items():
                if response_value == value:
                    return (response_field, indices)

        if isinstance(d, list):
            for index, subd in enumerate(d):
                key_and_index = (
                    _ReplaceRequestify._get_key_and_index_where_values_match(
                        value, subd, indices
                    )
                )
                if key_and_index:
                    key, prev_indices = key_and_index
                    prev_indices.append(index)
                    return (key, prev_indices)

    def _get_matching_field_and_indices(
        self, request: _RequestifyObject, value: Any
    ) -> tuple[Any, list[int]] | None:
        for (
            saved_request,
            saved_response,
        ) in self._requests_and_their_responses.items():
            # do not match responses returned by the same request we are trying to find matches for
            if saved_request == request:
                continue
            field, indices = self._get_key_and_index_where_values_match(
                value, saved_response
            ) or (None, [])
            if len(indices) > 0:
                # iterative recursion appends indices in reverse order,
                # so we need to reverse them to get the right order
                indices.reverse()

            return (field, indices)

    def _get_matching_request(self, request: _RequestifyObject, value: Any):
        for (
            saved_request,
            saved_response,
        ) in self._requests_and_their_responses.items():
            if saved_request == request:
                continue
            if self._get_key_and_index_where_values_match(value, saved_response):
                return saved_request
