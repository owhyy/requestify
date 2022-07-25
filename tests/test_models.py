import pytest

from requestify.utils import get_json_or_text, get_response
from requestify.models import _ReplaceRequestify, _RequestifyObject, _RequestifyList

EBS = "https://ebs.io"
GOOGLE = "https://google.com"
GITHUB = "https://github.com"


class TestRequestifyObject:
    # TODO: come up with a better name
    def assert_everything_matches(
        self, req, url=None, method=None, headers={}, data={}, cookies={}
    ):
        assert req._url == url
        assert req._method == method
        assert req._headers == headers
        assert req._data == data
        assert req._cookies == cookies

    @pytest.mark.parametrize("method", ("GET", "POST", "PUT", "PATCH", "HEAD"))
    def test_no_headers_no_data_no_cookies(self, method):
        req = _RequestifyObject(f"curl -X {method} {GOOGLE}")
        self.assert_everything_matches(req, GOOGLE, method.lower(), {}, {}, {})

    @pytest.mark.parametrize(
        "curl",
        (
            f"curl -X POST {GOOGLE} -H 'x: y'",
            f"curl {GOOGLE} -X POST -H 'x: y'",
            f"curl {GOOGLE} -H 'x: y' -X POST",
            f"curl -X POST -H 'x: y' {GOOGLE}",
            f"curl -H 'x: y' -X POST {GOOGLE}",
            f"curl     -X    POST    {GOOGLE}    -H     'x: y'",
        ),
    )
    def test_different_curl_positions(self, curl):
        req = _RequestifyObject(curl)
        self.assert_everything_matches(
            req=req,
            url=GOOGLE,
            method="post",
            headers={"x": "y"},
        )

    def test_with_headers_no_data_no_cookies(self):
        req = _RequestifyObject(f"""curl -X post {GOOGLE} -H 'x: y'""")

        self.assert_everything_matches(
            req=req, url=GOOGLE, method="post", headers={"x": "y"}, data={}, cookies={}
        )

    def test_with_no_headers_with_data_no_cookies(self):
        req = _RequestifyObject(f"""curl -X post {GOOGLE} -d '{{"x":"y"}}'""")

        self.assert_everything_matches(
            req=req, url=GOOGLE, method="post", headers={}, data={"x": "y"}, cookies={}
        )

    def test_with_no_headers_no_data_with_cookies(self):
        req = _RequestifyObject(
            f"""
        curl -X post {GOOGLE} -H "Cookie: cuki=sure"
        """
        )

        self.assert_everything_matches(
            req=req,
            url=GOOGLE,
            method="post",
            headers={},
            data={},
            cookies={"cuki": "sure"},
        )

    def test_curl_and_url_only(self):
        req = _RequestifyObject(f"curl {GOOGLE}")
        self.assert_everything_matches(req, GOOGLE, "get", {}, {}, {})

    # TODO: add more cases
    @pytest.mark.parametrize(
        "invalid_curl",
        (
            "",
            "qwerty",
        ),
    )
    def test_invalid_curl(self, invalid_curl):
        with pytest.raises(AssertionError):
            _RequestifyObject(f"{invalid_curl} {GOOGLE}")

    def test_lowercase_boolean_headers(self):
        req = _RequestifyObject(f"""curl -X post {GOOGLE} -H 'x: false' -H 'y: true'""")

        headers = {
            "x": "False",
            "y": "True",
        }

        self.assert_everything_matches(
            req=req, url=GOOGLE, method="post", headers=headers
        )

    def test_contains_flags(self):
        req = _RequestifyObject(
            f"curl -X POST {GOOGLE} -H 'content-type: application/json' --compressed;"
        )
        self.assert_everything_matches(
            req=req,
            url=GOOGLE,
            method="post",
            headers={"content-type": "application/json"},
        )

    def test_uses_data_handler(self):
        req = _RequestifyObject(
            f"""curl {GOOGLE} -d '{{"username":"nujabes", "password": "rip"}}' -H 'Accept: */*'"""
        )

        self.assert_everything_matches(
            req=req,
            url=GOOGLE,
            method="post",
            headers={"Accept": "*/*"},
            data={"username": "nujabes", "password": "rip"},
        )

    # TODO: add tests for different DATA_HANDLER flags


class TestRequestifyList(object):
    def test_list_generation(self):
        r1 = f"curl -X GET {GOOGLE}"
        r2 = f"curl -X GET {GITHUB}"
        r3 = f"curl -X GET {EBS}"

        assert _RequestifyList(r1, r2, r3)._requests == [
            _RequestifyObject(r1),
            _RequestifyObject(r2),
            _RequestifyObject(r3),
        ]

    def test_list_function_name_generation(self):
        r1 = f"curl -X GET {GOOGLE}"
        r2 = f"curl -X POST {GITHUB}"

        lorobj = _RequestifyList(r1, r1, r1, r2)
        function_names = [r._function_name for r in lorobj._requests]
        assert function_names == [
            "get_google_com",
            "get_google_com_1",
            "get_google_com_2",
            "post_github_com",
        ]
        assert lorobj._existing_function_names == {
            "get_google_com": 3,
            "post_github_com": 1,
        }


class TestReplaceRequestify(object):
    # we do this so we don't have to make requests for every test,
    # as it is both - slow and requires internet access
    def mock_get_responses(self, mocker):
        mocker.patch(
            "requestify.models.utils.get_responses",
            return_value=[{"data": 1}],
        )

    def test_replace_one_request(self, mocker):
        self.mock_get_responses(mocker)
        curl = f"curl -X GET {GOOGLE}"
        r = _ReplaceRequestify(curl)
        assert r._requests == [_RequestifyObject(curl)]
        assert r._function_names_and_their_responses == {"get_google_com": {"data": 1}}
        assert r._matching_data == {}

    def test_replace_requests_no_data_to_replace(self, mocker):
        mocker.patch(
            "requestify.models.utils.get_responses",
            #               GET          POST
            return_value=[{"foo": "bar"}, {"foo": "xyz"}],
        )
        curl = f"curl -X GET {GOOGLE}"
        nodata_curl = f"curl -X POST {GOOGLE}"
        r = _ReplaceRequestify(curl, nodata_curl)
        assert r._function_names_and_their_responses == {
            "get_google_com": {"foo": "bar"},
            "post_google_com": {"foo": "xyz"},
        }
        assert r._matching_data == {}

    def test_initialize_responses_dict(self, mocker):
        self.mock_get_responses(mocker)
        r = f"curl -X GET {GOOGLE}"
        mocker.patch("tests.test_models.get_response", return_value={"data": 1})
        response = get_response(_RequestifyObject(r))
        rr = _ReplaceRequestify(r)
        assert rr._function_names_and_their_responses == {"get_google_com": {"data": 1}}

    def test_has_matching_null_data(self, mocker):
        mocker.patch(
            "requestify.models.utils.get_responses",
            #               GET          POST
            return_value=[{"data": None}, {"something": None}],
        )
        r1 = f"curl -X GET {GOOGLE}"
        r2 = f"""curl -X POST -d '{{"data": None"}}' {GOOGLE}"""
        rr = _ReplaceRequestify(r1, r2)
        assert rr._matching_data == {}

    def test_has_matching_data_dict(self, mocker):
        mocker.patch(
            "requestify.models.utils.get_responses",
            #               GET          POST
            return_value=[{"foo": 1}, {"something": 1}],
        )
        r1 = f"curl -X GET {GOOGLE}"
        r2 = f"""curl -X POST -d '{{"bar": 1}}' {GOOGLE}"""
        rr = _ReplaceRequestify(r1, r2)
        assert rr._matching_data == {"post_google_com['bar']": "get_google_com['foo']"}

    def test_has_matching_data_list(self, mocker):
        mocker.patch(
            "requestify.models.utils.get_responses",
            #               GET                 POST
            return_value=[{"foo": [1, 2, 3]}, {"bar": [1, 2, 3]}],
        )
        r1 = f"curl -X GET {GOOGLE}"
        r2 = f"""curl -X POST -d '{{"bar": [1, 2, 3]}}' {GOOGLE}"""
        rr = _ReplaceRequestify(r1, r2)
        assert rr._matching_data == {"post_google_com['bar']": "get_google_com['foo']"}

    def test_has_matching_data_string(self, mocker):
        mocker.patch(
            "requestify.models.utils.get_responses",
            #               GET          POST
            return_value=["foo", "foo"],
        )
        r1 = f"curl -X GET {GOOGLE}"
        r2 = f"""curl -X POST -d '{{"data": [1, 2, 3]}}' {GOOGLE}"""
        rr = _ReplaceRequestify(r1, r2)
        assert rr._matching_data == {}
