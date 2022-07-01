import unittest
import requests
import requestify
import re

EBS = "https://ebs.io"
GOOGLE = "https://google.com"
GITHUB = "https://github.com"


class TestRequestify(unittest.TestCase):
    def check_equal(self, my_response, response):
        self.assertEqual(my_response.url, response.url)
        self.assertEqual(my_response.headers, response.headers)
        self.assertEqual(my_response.data, response.data)
        self.assertEqual(my_response.cookies, response.cookies)

    def check(self, url, curl="", headers={}, cookies={}):
        if not curl:
            curl = f"""curl -X GET {url}"""
        response = requests.get(url, headers=headers, cookies=cookies)
        my_response = requestify.from_string(curl)

        self.assertEqual(my_response.url.rstrip("/"), response.url.rstrip("/"))
        # response.headers returns more headers that those passed, so we'll just test the response text instead
        self.assertEqual(my_response.execute().strip("\n"), response.text.strip("\n"))

        # wish we could do something like
        # if headers:
        #     self.assertRegex(response.headers.values(), my_response.headers.values())
        # if cookies:
        #     self.assertEqual(my_response.cookies, response.cookies)
        # if data:
        #     self.assertEqual(my_response.data, response.raw)

    def test_flag_get_address(self):
        self.check(EBS)

    def test_address_flag_get(self):
        self.check(EBS, f'curl "{EBS}" -X GET')

    def test_headers(self):
        curl = f"""curl -X GET "{EBS}" \
       -H 'Accept: application/json, text/plain, */*' \
       -H 'Accept-Language: en' \
       -H 'Connection: keep-alive'"""

        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en",
            "Connection": "keep-alive",
        }

        self.check(EBS, curl=curl, headers=headers)

    def test_cookies(self):
        curl = """
        curl "https://github.com" -X GET \
        -H 'Cookie:
        logged_in=yes; user_session=this_is_a_cookie; xyz=qwerty;'
        """

        cookies = {
            "logged_in": "yes",
            "usser_session": "this_is_a_cookie",
            "xyz": "querty",
        }

        response = requests.get(GITHUB, cookies=cookies)
        my_response = requestify.from_string(curl)
        # we can't check for data because it's generated randomly
        self.assertEqual(response.url.strip("/"), my_response.url.strip("/"))

    def test_noflag_get_address(self):
        curl = '''curl GET "https://google.com"'''

        with self.assertRaises(AssertionError):
            try:
                requestify.from_string(curl)
            except AssertionError:
                raise

    def test_nomethod_noflag_get_address(self):
        self.check(EBS, curl=f'curl "{EBS}"')

    def test_flag_post_address(self):
        curl = f"curl -X POST {GITHUB}"
        response = requests.post(GITHUB)
        my_response = requestify.from_string(curl)

        self.assertEqual(my_response.method, "post")
        self.assertEqual(my_response.execute().strip("\n"), response.text.strip("\n"))

    def test_nomethod_noflag_has_data_address(self):
        curl = f"""curl "{EBS}" --data-raw '{{"username":"Test123","password":"Test123"}}'"""

        data = {"username": "Test123", "password": "Test123"}
        response = requests.post(EBS, data=data)

        my_response = requestify.from_string(curl)

        self.assertEqual(my_response.method, "post")
        self.assertEqual(my_response.url.strip("/"), response.url.strip("/"))

    def test_noprotocol_url(self):  # todo
        self.check(EBS, curl='curl -X GET "ebs.io"')

    def test_noquotes_url(self):
        self.check(EBS, curl="curl -X GET https://ebs.io")

    def test_dotted_domain_name(self):
        url = "https://drf-yasg.readthedocs.io/en/stable/"
        self.check(url, curl=f'curl -X GET "{url}"')

    def test_noprotocol_www_hostname(self):  # todo
        self.check(GOOGLE, curl=f'curl -X GET "www.google.com"')

    def test_www_hostname(self):
        url = "www.google.comresponse.urlresponse.url"
        self.check(url, curl=f'curl -X GET "{url}"')

    def test_resource(self):
        self.check(
            f"{GOOGLE}/search?q=cats",
            curl='curl -X GET "https://www.google.com/search?q=cats"',
        )

    def test_no_url(self):
        self.assertRaises(Exception, requestify.from_string("curl"))

    def test_spaces_in_curl(self):
        self.check(EBS, curl=f'curl   -X    GET     "{EBS}"')

    # this should be ignored I guess?
    def test_chrome_extension_url(self):
        curl = """
        curl 'chrome-extension://fmkadmapgofadopljbjfkapdkoienihi/build/react_devtools_backend.js' \
        -H 'Referer: ' \
        -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36' \
        --compressed ;
        """

    def test_base(self):
        pass

    def test_beautify(self):
        curl = """
        curl "https://google.com" -X GET
        """

        correct_requests = """import requests

headers = {}
cookies = {}
response = requests.get("https://google.com", headers=headers, cookies=cookies)
print(response.text)
"""

        actual_requests = requestify.from_string(curl).create_beautiful_response()
        self.assertEqual(correct_requests, actual_requests)

    def test_has_separator(self):
        url = "https://eurasia-precept-api.devebs.net/users/login"
        curl = f"""
curl '{url}' -X 'OPTIONS' \
  -H 'Accept: */*' \
  -H 'Accept-Language: en-US,en;q=0.9,ro;q=0.8' \
        """

        headers = {"Accept": "*/*", "Accept-Language": "en-US,en;q=0.9,ro;q=0.8"}

        response = requests.options(url, headers=headers)
        my_response = requestify.from_string(curl)
        self.assertEqual(my_response.url, response.url)
        self.assertEqual(my_response.method, "options")
        self.assertEqual(my_response.execute().strip("\n"), response.text.strip("\n"))

    # def test_from_file(self):
    #     self.assertEqual(requestify.from_file('curls'), [])

    def test_false_replace(self):
        self.assertEqual(requestify.from_file("curls"), [])


class TestRequestifyList(unittest.TestCase):
    def test_list_create_responses_text(self):
        pass

    def test_create_function_name(self):
        pass

    def test_from_file(self):
        requestify.from_file("curls").to_screen()
