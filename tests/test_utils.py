import pytest
from requestify import utils

GOOGLE = 'https://google.com'


class TestUtils:
    def test_format_url(self):
        assert utils.format_url('//url.com') == '//url.com'
        assert utils.format_url('http://url.com') == 'http://url.com'
        assert utils.format_url('https://url.com') == 'https://url.com'

        assert utils.format_url('url.com') == 'https://url.com'

    @pytest.mark.parametrize(
        's, url',
        [
            ('google.com', 'google.com'),
            (GOOGLE, GOOGLE),
            ('http://google.com', 'http://google.com'),
            ('https://google.com', 'https://google.com'),
            ('www.google.com', 'www.google.com'),
            ('https://www.google.com', 'https://www.google.com'),
            ('//www.google.com', 'www.google.com'),
            ('//google.com', 'google.com'),
            ('oogabooga://google.com', 'google.com'),
            ('has.dots.in.domain', 'has.dots.in.domain'),
            (f'some more words {GOOGLE} 1234', GOOGLE),
            (f'{GOOGLE} google.com http://google.com', GOOGLE),
        ],
    )
    def test_find_url_or_error_valid(self, s, url):
        assert utils.find_url_or_error(s) == url

    # def test_find_url_or_error_throws(self):
    #     with pytest.raises(ValueError):
    #         requestify.find_url_or_error([])

    def test_get_strings_without_url(self):
        assert (
            utils.get_strings_without_url('google.com', ['google.com']) == []
        )
        assert utils.get_strings_without_url(
            'google.com', ['google.com', 'youtube.com', 'github.com']
        ) == ['youtube.com', 'github.com']

    def test_uppercase_boolean_values(self):
        opts = [('x', 'true'), ('y', 'false')]
        assert [
            ('x', 'True'),
            ('y', 'False'),
        ] == utils.uppercase_boolean_values(opts)

    def test_find_and_get_opts(self):
        meta = "-X POST oogabooga.com -H 'good: yes' -H 'ok: notok'"
        opts = ['-H', 'good: yes', '-H', 'ok: notok']

        assert utils.find_and_get_opts(meta) == opts

    def test_split_list(self):
        assert utils.split_list(['ok', 'ok 123 booya']) == [
            'ok',
            'ok',
            '123',
            'booya',
        ]

    # def test_get_json_or_text(self, arg):
    #     r = RequestifyObject(f"curl -X get {GOOGLE}")
    #     assert utils.get_json_or_text(r) ==
