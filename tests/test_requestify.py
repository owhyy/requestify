import pytest
import requests
from requestify import requestify

EBS = "https://ebs.io"
GOOGLE = "https://google.com"
GITHUB = "https://github.com"

REQUEST_VARIABLE_NAME = "request"


class TestRequestifyObject:
    # TODO: come up with a better name
    def assert_everything_matches(
        self, req, url=None, method=None, headers={}, data={}, cookies={}
    ):
        assert req.url == url
        assert req.method == method
        assert req.headers == headers
        assert req.data == data
        assert req.cookies == cookies

    @pytest.mark.parametrize("method", ("GET", "POST", "PUT", "PATCH", "HEAD"))
    def test_no_headers_no_data_no_cookies(self, method):
        req = requestify.RequestifyObject(f"curl -X {method} {GOOGLE}")
        self.assert_everything_matches(req, GOOGLE, method.lower(), {}, {}, {})

    @pytest.mark.parametrize(
        "curl",
        (
            f"curl -X POST {GOOGLE} -H 'content-type: application/json'",
            f"curl {GOOGLE} -X POST -H 'content-type: application/json'",
            f"curl {GOOGLE} -H 'content-type: application/json' -X POST ",
            f"curl -X POST -H 'content-type: application/json' {GOOGLE}",
            f"curl -H 'content-type: application/json' -X POST {GOOGLE}",
            f"curl     -X    POST    {GOOGLE}    -H     'content-type: application/json'",
        ),
    )
    def test_different_curl_positions(self, curl):
        req = requestify.RequestifyObject(curl)
        self.assert_everything_matches(
            req=req, url=GOOGLE, method="post", data={"content-type: application/json"}
        )

    def test_with_headers_no_data_no_cookies(self):
        req = requestify.RequestifyObject(
            f"""curl -X post {GOOGLE} -H 'accept: application/json' -H 'X-CSRFToken: wRL3SoeQUYlKXdJ3VtQORHDjMgplSOBfwwTM24zUZHfimB5LUMw3Xfmii1jHmjFK' """
        )

        headers = {
            "accept": "application/json",
            "X-CSRFToken": "wRL3SoeQUYlKXdJ3VtQORHDjMgplSOBfwwTM24zUZHfimB5LUMw3Xfmii1jHmjFK",
        }

        self.assert_everything_matches(req, GOOGLE, "post", headers, {}, {})

    def test_with_no_headers_with_data_no_cookies(self):
        req = requestify.RequestifyObject(f"""curl -X post  """)

        data = {
            "accept": "application/json",
            "X-CSRFToken": "wRL3SoeQUYlKXdJ3VtQORHDjMgplSOBfwwTM24zUZHfimB5LUMw3Xfmii1jHmjFK",
        }

        self.assert_everything_matches(req, GOOGLE, "post", headers, {}, {})

    def test_curl_and_url_only(self):
        req = requestify.RequestifyObject(f"curl {GOOGLE}")
        self.assert_everything_matches(req, GOOGLE, "get", {}, {}, {})

    @pytest.mark.parametrize("method", ("GET", "POST", "PUT", "PATCH", "HEAD"))
    def test_base_response_no_headers_no_data_no_cookies(self, method):
        req = requestify.RequestifyObject(f"curl -X {method} {GOOGLE}")
        base_method = [
            "headers = {}",
            "cookies = {}",
            f"{REQUEST_VARIABLE_NAME} = requests.{req.method}('{req.url}', headers=headers, cookies=cookies)",
        ]
        assert req.create_responses_base() == base_method

    def test_base_response_with_headers_no_data_no_cookies(self):
        req = requestify.RequestifyObject(
            f"""curl -X post {GOOGLE} -H 'accept: application/json' -H 'X-CSRFToken: wRL3SoeQUYlKXdJ3VtQORHDjMgplSOBfwwTM24zUZHfimB5LUMw3Xfmii1jHmjFK'"""
        )
        base_method = [
            """headers = {'accept: application/json', 'X-CSRFToken: wRL3SoeQUYlKXdJ3VtQORHDjMgplSOBfwwTM24zUZHfimB5LUMw3Xfmii1jHmjFK'}""",
            "cookies = {}",
            f"{REQUEST_VARIABLE_NAME} = requests.{req.method}('{req.url}', headers=headers, cookies=cookies)",
        ]
        assert req.create_responses_base() == base_method

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
            requestify.RequestifyObject(f"{invalid_curl} {GOOGLE}")

    def test_lowercase_boolean_headers(self):
        req = requestify.RequestifyObject(
            f"""curl -X post {GOOGLE} -H 'something: false' -H 'something_else: true'"""
        )

        headers = {
            "something": "False",
            "something_else": "True",
        }

        self.assert_everything_matches(req=req, url=GOOGLE, method="post", data=headers)

    def test_method_url_headers(self):
        pass

    def test_url_method_headers(self):
        pass

    def test_get_url(self):
        opts = """-H 'accept: application/json' -H 'X-CSRFToken: wRL3SoeQUYlKXdJ3VtQORHDjMgplSOBfwwTM24zUZHfimB5LUMw3Xfmii1jHmjFK'"""
        curl = f"""curl -X post {GOOGLE} {opts}"""

        assert opts == requestify.RequestifyObject.get_opts_string(curl)

    def test_add_scheme_to_url(self):
        pass

    def test_find_url_or_error_valid(self):
        pass

    def test_find_url_or_error_throws(self):
        pass

    def test_pairwise(self):
        pass

    def test_uppercase_boolean_values(self):
        opts = [('x', "true"), ('y', "false")]
        assert [('x', "True"), ('y', "False")] == requestify.uppercase_boolean_values(opts)

    def test_get_opts(self):
        pass

    def test_create_beautiful(self):
        pass

    def test_to_screen(self):
        pass

    def test_to_file(self):
        pass

    def test_more_headers(self):
        req = requestify.RequestifyObject(
            """curl 'https://main.api.dev.ebs.io/users/login/user/' \
      -X 'OPTIONS' \
      -H 'Accept: */*' \
      -H 'Accept-Language: en-US,en;q=0.9,ro;q=0.8' \
      -H 'Access-Control-Request-Headers: authorization,content-type' \
      -H 'Access-Control-Request-Method: POST' \
      -H 'Connection: keep-alive' \
      -H 'Origin: https://nemo.dev.ebs.io' \
      -H 'Referer: https://nemo.dev.ebs.io/' \
      -H 'Sec-Fetch-Dest: empty' \
      -H 'Sec-Fetch-Mode: cors' \
      -H 'Sec-Fetch-Site: same-site' \
      -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36' \'"""
        )
        assert req == req

    def test_remove_url_from_list_of_strings(self):
        pass

class RequestifyListTest:
    def test_init(self):
        pass

    def test_create_responses_base(self):
        pass

    def test_create_beautiful(self):
        pass

    def test_to_screen(self):
        pass

    def test_to_file(self):
        pass
