import pytest
from requestify.models import ReplaceRequestify, RequestifyObject, RequestifyList

EBS = "https://ebs.io"
GOOGLE = "https://google.com"
GITHUB = "https://github.com"


class TestModels:
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
        req = RequestifyObject(f"curl -X {method} {GOOGLE}")
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
        req = RequestifyObject(curl)
        self.assert_everything_matches(
            req=req,
            url=GOOGLE,
            method="post",
            headers={"x": "y"},
        )

    def test_with_headers_no_data_no_cookies(self):
        req = RequestifyObject(f"""curl -X post {GOOGLE} -H 'x: y'""")

        self.assert_everything_matches(
            req=req, url=GOOGLE, method="post", headers={"x": "y"}, data={}, cookies={}
        )

    def test_with_no_headers_with_data_no_cookies(self):
        req = RequestifyObject(f"""curl -X post {GOOGLE} -d '{{"x":"y"}}'""")

        self.assert_everything_matches(
            req=req, url=GOOGLE, method="post", headers={}, data={"x": "y"}, cookies={}
        )

    def test_with_no_headers_no_data_with_cookies(self):
        req = RequestifyObject(
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
        req = RequestifyObject(f"curl {GOOGLE}")
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
            RequestifyObject(f"{invalid_curl} {GOOGLE}")

    def test_lowercase_boolean_headers(self):
        req = RequestifyObject(f"""curl -X post {GOOGLE} -H 'x: false' -H 'y: true'""")

        headers = {
            "x": "False",
            "y": "True",
        }

        self.assert_everything_matches(
            req=req, url=GOOGLE, method="post", headers=headers
        )

    def test_contains_flags(self):
        req = RequestifyObject(
            f"curl -X POST {GOOGLE} -H 'content-type: application/json' --compressed;"
        )
        self.assert_everything_matches(
            req=req,
            url=GOOGLE,
            method="post",
            headers={"content-type": "application/json"},
        )

    def test_uses_data_handler(self):
        req = RequestifyObject(
            f"""curl {GOOGLE} -d '{{"username":"nujabes", "password": "rip"}}' -H 'Accept: */*'"""
        )

        self.assert_everything_matches(
            req=req,
            url=GOOGLE,
            method="post",
            headers={"Accept": "*/*"},
            data={"username": "nujabes", "password": "rip"},
        )

    def test_list_generation(self):
        r1 = f"curl -X GET {GOOGLE}"
        r2 = f"curl -X GET {GITHUB}"
        r3 = f"curl -X GET {EBS}"

        assert RequestifyList(r1, r2, r3).requests == [
            RequestifyObject(r1),
            RequestifyObject(r2),
            RequestifyObject(r3),
        ]

    def test_list_function_name_generation(self):
        r1 = f"curl -X GET {GOOGLE}"
        r2 = f"curl -X POST {GITHUB}"

        lorobj = RequestifyList(r1, r1, r1, r2)
        function_names = [r.function_name for r in lorobj.requests]
        assert function_names == [
            "get_google_com",
            "get_google_com_1",
            "get_google_com_2",
            "post_github_com",
        ]
        assert lorobj.existing_function_names == {
            "get_google_com": 3,
            "post_github_com": 1,
        }

    def test_replace_one_request(self):
        r = f"curl -X GET {GOOGLE}"
        assert ReplaceRequestify(r).requests[0] == RequestifyObject(r)

    def initialize_responses_dict(self):
        pass

    def test_replace_requests_no_data_to_replace(self):
        r = f"curl -X GET {GOOGLE}"
        nd_r = f"curl -X POST {GITHUB}"

        robj = ReplaceRequestify(r, nd_r)
        assert robj.requests[1].data == {} == RequestifyObject(nd_r).data
