import string

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from shurls.logic import CharChainsGenerator

TEST_SERVER_ADDRESS = "http://testserver"
client = APIClient()


@pytest.mark.django_db
class TestOriginalUrlView:
    def test_shorten_correct_url(self):
        response = client.post(TEST_SERVER_ADDRESS, {"url": "http://minifesto.org/"}, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data.get("short_url") == "http://testserver/9gsi"

    def test_redirect_to_original_url(self):
        url = "http://minifesto.org/"
        short_url = client.post(TEST_SERVER_ADDRESS, {"url": url}, format="json").data.get("short_url")
        # sanity check
        assert short_url.startswith(TEST_SERVER_ADDRESS)

        response = client.get(short_url)
        assert response.status_code == status.HTTP_302_FOUND
        assert response.url == url

    @pytest.mark.parametrize(
        "url",
        (
            # invalid host
            "http://minifestoorg",
            # invalid protocol
            "httx://minifesto.org/",
            "minifesto.org/",
            "file://minifesto.org/",
            # malicious url
            "javascript:alert('hacked!');",
            "http://www.circl.lu/a.php?rm -Rf /etc",
            "https://minifesto.org/<script>alert('got you!')</script>",
        ),
    )
    def test_create_short_url_unprocessable_entity(self, url: str):
        response = client.post(TEST_SERVER_ADDRESS, {"url": url}, format="json")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.parametrize(
        "data",
        (
            None,
            {},
            {"random": 123},
            {"urlx": "http://minifesto.org/"},
            {"URL": "http://minifesto.org/"},
            {"_url": "http://minifesto.org/"},
        ),
    )
    def test_create_short_url_bad_request(self, data: dict):
        response = client.post(TEST_SERVER_ADDRESS, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize(
        "short_url, expected_status",
        (
            # invalid path
            (f"{TEST_SERVER_ADDRESS}/param1=abcd", status.HTTP_400_BAD_REQUEST),
            (f"{TEST_SERVER_ADDRESS}/xyz&param1=abcd", status.HTTP_400_BAD_REQUEST),
            # invalid short url: contains characters from outside the alphabet
            (f"{TEST_SERVER_ADDRESS}/Jq4!A..D", status.HTTP_400_BAD_REQUEST),
            # invalid short url: no such entry
            (f"{TEST_SERVER_ADDRESS}/9gs", status.HTTP_404_NOT_FOUND),
            (f"{TEST_SERVER_ADDRESS}/9g5i", status.HTTP_404_NOT_FOUND),
            (f"{TEST_SERVER_ADDRESS}/abcxyz", status.HTTP_404_NOT_FOUND),
            (f"{TEST_SERVER_ADDRESS}/xyz?abcd", status.HTTP_404_NOT_FOUND),
        ),
    )
    def test_redirect_to_original_url_bad_request(self, short_url: str, expected_status: int):
        client.post(TEST_SERVER_ADDRESS, {"url": "http://minifesto.org/"}, format="json")
        # sanity check
        assert client.get(f"{TEST_SERVER_ADDRESS}/9gsi").status_code == status.HTTP_302_FOUND

        response = client.get(short_url)
        assert response.status_code == expected_status


class TestCharChainsGenerator:
    @pytest.mark.parametrize(
        "n, alphabet, min_len, expected",
        (
            # consecutive numbers have distant results
            (1, "abcde01234", 3, "4ae"),
            (2, "abcde01234", 3, "ca4"),
            (330, "abcde01234", 3, "bac1"),
            (9999999, "abcde01234", 3, "234baeab4"),
            # using different alphabets generates different results
            (1000, "abcd", 3, "dbbcbccb"),
            (1000, "abcde", 3, "aaacce"),
            (1000, string.ascii_letters, 3, "WmS"),
            (1000, string.ascii_lowercase, 3, "uebk"),
            (1000, string.digits, 3, "64994"),
            (1000, string.punctuation, 3, "://;"),
            # using different min length generates different results
            (1825, string.ascii_letters, 3, "BKo"),
            (1825, string.ascii_letters, 7, "BKoPdmk"),
            (1825, string.ascii_letters, 10, "BKoPdmkUYl"),
        ),
    )
    def test_encode(self, n: int, alphabet: str, min_len: int, expected: str):
        assert CharChainsGenerator(alphabet, min_len=min_len).encode(n) == expected

    @pytest.mark.parametrize(
        "alphabet, min_len, chain, expected",
        (
            # similar chains have distant results
            (string.ascii_lowercase + string.digits, 3, "abc999", 2119790),
            (string.ascii_lowercase + string.digits, 3, "abc000", 2136183),
            (string.ascii_lowercase + string.digits, 3, "abc001", 61033),
            # chains have different origin in different alphabets
            ("abcde", 3, "abc", 6),
            ("abcde01234", 3, "abc", 22),
            (string.ascii_lowercase, 3, "abc", 513),
            (string.ascii_letters, 3, "abc", 1399),
            (string.ascii_letters + string.digits, 3, "abc", 2760),
            # using different min length generates same results
            ("abcde01234", 3, "aaabbbccc", 42648322),
            ("abcde01234", 5, "aaabbbccc", 42648322),
            ("abcde01234", 7, "aaabbbccc", 42648322),
            ("abcde01234", 9, "aaabbbccc", 42648322),
        ),
    )
    def test_decode(self, alphabet: str, min_len: int, chain: str, expected: int):
        assert CharChainsGenerator(alphabet, min_len=min_len).decode(chain) == expected

    @pytest.mark.parametrize(
        "alphabet, min_len, chain",
        (
            # cannot decode if characters outside the alphabet
            (string.ascii_lowercase, 3, "ABC"),
            (string.ascii_lowercase, 3, "abc012"),
            (string.ascii_lowercase, 3, "xyz!"),
            # cannot decode if chain shorter than min length
            (string.ascii_lowercase, 10, "aaabbb"),
            (string.ascii_lowercase, 5, "abc"),
        ),
    )
    def test_decode_incorrect_chains(self, alphabet: str, min_len: int, chain: str):
        with pytest.raises(ValueError):
            CharChainsGenerator(alphabet, min_len=min_len).decode(chain)

    @pytest.mark.parametrize(
        "alphabet, seed, expected",
        (
            # using original alphabet if seed not provided
            ("abcde", None, "abcde"),
            ("abcde0123", None, "abcde0123"),
            ("edcba", None, "edcba"),
            (string.ascii_letters, None, string.ascii_letters),
            # same seed, same alphabet every time
            ("abcde", 6, "dcbae"),
            ("abcde", 6, "dcbae"),
            ("abcde", 6, "dcbae"),
            # different seeds, different order of chars in alphabet
            ("abcde", 0, "cbaed"),
            ("abcde", 1, "cdeab"),
            ("abcde", 2, "cbdea"),
            ("abcde", 137, "ecdba"),
            # for short alphabet all possible combinations will be quickly exhausted
            # so using different seeds can lead to generating the same alphabet
            # see also: [this thread in SO](https://stackoverflow.com/q/77212579)
            ("abcde", 0, "cbaed"),
            ("abcde", 344, "cbaed"),
            ("abcde", 398, "cbaed"),
            ("abcde", 496, "cbaed"),
        ),
    )
    def test_using_seed(self, alphabet: str, seed: int, expected: str):
        assert CharChainsGenerator(alphabet, seed=seed).alphabet == expected
