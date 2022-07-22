import pytest
import requests
from requestify import requestify

EBS = "https://ebs.io"
GOOGLE = "https://google.com"
GITHUB = "https://github.com"


class TestMetods:
    @pytest.mark.parametrize("url", ("google.com", GOOGLE))
    def test_format_url(self, url):
        assert requestify.format_url(url) == GOOGLE

    @pytest.mark.parametrize(
        "s, url",
        [
            ("google.com", "google.com"),
            (GOOGLE, GOOGLE),
            ("http://google.com", "http://google.com"),
            ("https://google.com", "https://google.com"),
            ("www.google.com", "www.google.com"),
            ("https://www.google.com", "https://www.google.com"),
            ("//www.google.com", "www.google.com"),
            ("//google.com", "google.com"),
            ("oogabooga://google.com", "google.com"),
            ("has.dots.in.domain", "has.dots.in.domain"),
            (f"some more words {GOOGLE} 1234", GOOGLE),
            (f"{GOOGLE} google.com http://google.com", GOOGLE),
        ],
    )
    def test_find_url_or_error_valid(self, s, url):
        assert requestify.find_url_or_error(s) == url

    # def test_find_url_or_error_multiple_throws(self):
    #     with pytest.raises(ValueError):
    #         requestify.find_url_or_error([])

    @pytest.mark.parametrize(
        "los, res",
        [
            (["google.com"], []),
            (
                ["something", "google.com", "something else"],
                ["something", "something else"],
            ),
            (10 * ["google.com"], []),
        ],
    )
    def test_get_list_of_strings_without_url(self, los, res):
        assert requestify.get_list_of_strings_without_url(los, "google.com") == res

    def test_uppercase_boolean_values(self):
        opts = [("x", "true"), ("y", "false")]
        assert [("x", "True"), ("y", "False")] == requestify.uppercase_boolean_values(
            opts
        )

    def test_find_and_get_opts(self):
        meta = "-X POST oogabooga.com -H 'good: yes' -H 'ok: notok'"
        opts = ["-H", "good: yes", "-H", "ok: notok"]

        assert requestify.find_and_get_opts(meta) == opts

    def test_flatten_list(self):
        assert requestify.split_and_flatten_list(["ok", "ok 123 booya"]) == [
            "ok",
            "ok",
            "123",
            "booya",
        ]


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

    # Class tests
    @pytest.mark.parametrize("method", ("GET", "POST", "PUT", "PATCH", "HEAD"))
    def test_no_headers_no_data_no_cookies(self, method):
        req = requestify.RequestifyObject(f"curl -X {method} {GOOGLE}")
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
        req = requestify.RequestifyObject(curl)
        self.assert_everything_matches(
            req=req,
            url=GOOGLE,
            method="post",
            headers={"x": "y"},
        )

    def test_with_headers_no_data_no_cookies(self):
        req = requestify.RequestifyObject(f"""curl -X post {GOOGLE} -H 'x: y'""")

        self.assert_everything_matches(
            req=req, url=GOOGLE, method="post", headers={"x": "y"}, data={}, cookies={}
        )

    def test_with_no_headers_with_data_no_cookies(self):
        req = requestify.RequestifyObject(f"""curl -X post {GOOGLE} -d '{{"x":"y"}}'""")

        self.assert_everything_matches(
            req=req, url=GOOGLE, method="post", headers={}, data={"x": "y"}, cookies={}
        )

    def test_with_no_headers_no_data_with_cookies(self):
        req = requestify.RequestifyObject(
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
        req = requestify.RequestifyObject(f"curl {GOOGLE}")
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
            requestify.RequestifyObject(f"{invalid_curl} {GOOGLE}")

    def test_lowercase_boolean_headers(self):
        req = requestify.RequestifyObject(
            f"""curl -X post {GOOGLE} -H 'x: false' -H 'y: true'"""
        )

        headers = {
            "x": "False",
            "y": "True",
        }

        self.assert_everything_matches(
            req=req, url=GOOGLE, method="post", headers=headers
        )

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

    def test_contains_flags(self):
        req = requestify.RequestifyObject(
            f"curl -X POST {GOOGLE} -H 'content-type: application/json' --compressed;"
        )
        self.assert_everything_matches(
            req=req,
            url=GOOGLE,
            method="post",
            headers={"content-type": "application/json"},
        )

    def test_uses_data_handler(self):
        req = requestify.RequestifyObject(
            f"""curl {GOOGLE} -d '{{"username":"nujabes", "password": "rip"}}' -H 'Accept: */*'"""
        )

        self.assert_everything_matches(
            req=req,
            url=GOOGLE,
            method="post",
            headers={"Accept": "*/*"},
            data={"username": "nujabes", "password": "rip"},
        )

    def test_create_beautiful_response(self):
        req = requestify.RequestifyObject(f"""curl -X post {GOOGLE} -H 'x: y'""")
        beautiful = f"""
class {CLASS_NA}
        """

    def test_to_screen(self):
        pass

    def test_to_file(self):
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
