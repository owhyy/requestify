import pytest
from requestify import utils

GOOGLE = "https://google.com"

class TestUtils:
    @pytest.mark.parametrize("url", ("google.com", GOOGLE))
    def test_format_url(self, url):
        assert utils.format_url(url) == GOOGLE

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
        assert utils.find_url_or_error(s) == url

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
        assert utils.get_list_of_strings_without_url(los, "google.com") == res

    def test_uppercase_boolean_values(self):
        opts = [("x", "true"), ("y", "false")]
        assert [("x", "True"), ("y", "False")] == utils.uppercase_boolean_values(
            opts
        )

    def test_find_and_get_opts(self):
        meta = "-X POST oogabooga.com -H 'good: yes' -H 'ok: notok'"
        opts = ["-H", "good: yes", "-H", "ok: notok"]

        assert utils.find_and_get_opts(meta) == opts

    def test_flatten_list(self):
        assert utils.split_and_flatten_list(["ok", "ok 123 booya"]) == [
            "ok",
            "ok",
            "123",
            "booya",
        ]
