from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response

from short_URLs.settings import ALPHABET, SEED
from shurls.logic import CharChainsGenerator
from shurls.models import URL

short_urls_generator = CharChainsGenerator(alphabet=ALPHABET, seed=SEED)
url_validator = URLValidator()


class OriginalUrlView(generics.CreateAPIView):
    def create(self, request, *args, **kwargs):
        """
        Return the object containing short url generated for the given original url.

        If the given URL format is invalid, method would raise 422 UNPROCESSABLE ENTITY error.
        If the given request does not follow the specified schema, method would raise 400 BAD REQUEST error.

        The short URL will not be stored in the database, but will be generated on-fly, based on
        the database ID of the provided URL.
        Short URL will be generated using bijective function with the record id as an argument.
        This would allow to convert the short url back into record ID, allowing to decode the short URL
        into it's original URL.

        Proposed approach has both pros and cons.

        (P1) Decision to generate short URL on fly would allow to limit the columns of the URL record
        stored in the database and the number of indexes. In case of storing shortened version of the URL,
        this column should be indexed to optimize SELECT requests when retrieving urls from database.
        With the selected approach, only primary key ID column is relevant and no other index is required.

        (P2) There is no need to ensure uniqueness of the original URL. Since short URL generation based on
        the record ID, it is possible to have a duplicated original URLs with different shortened versions.
        This is not harmful scenario, as still all the short URLs would be unique (as record IDs have to be unique),
        so they still can be unambiguously translated into the original URL.
        Allowing duplicated original URLs make possible to skip expensive EXISTS check on every POST request
        to create short URL.

        (C1) Generating short URLs on fly has a single major consequence of being sensitive to the data consistency.
        Every such operation, as listed below, can harm the bidirectional conversion between original and short URLs
        and cause strange application behaviours, like not recognizing self-created short URLS:
         - changing record ID
         - changing CharChainsGenerator underlying alphabet
         - using different seeds for alphabet shuffling on the application (re)start
         - resetting AUTO_INCREMENT to arbitrarily selected value

        Any of the above operation should be considered as potential danger to the application reliability
        and consistency. Thus, if there exists an important use case to perform one of those operations,
        then short URL generation design should be re-considered for change.
        """
        if not (original_url := request.data.get("url")):
            return Response("Missing required information in request body", status=status.HTTP_400_BAD_REQUEST)

        if not self._is_valid(original_url):
            return Response(f"Invalid URL passed: {original_url}", status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        url = URL(url=original_url)
        url.save()

        base_url = request.build_absolute_uri()
        short_url_path = short_urls_generator.encode(url.id)
        return Response({"short_url": base_url + short_url_path}, status=status.HTTP_201_CREATED)

    @staticmethod
    def _is_valid(url: str) -> bool:
        """Check if the given url is formatted correctly."""
        try:
            url_validator(url)
            return True
        except ValidationError:
            return False


class ShortUrlsView(generics.RetrieveAPIView):
    def get(self, request, *args, **kwargs):
        """
        Redirect to the original URL based on the short URL path from the requested URL.

        If the requested URL is not known, the method will raise 404 NOT FOUND error.
        If the short URL path from requested URL has invalid format, method would raise 400 BAD REQUEST error.

        The short URL path from requested url is converted to the database record ID storing the original URL.
        Reverse translation is performed by the same generator that was used at first to convert
        original URL into its shortened version.
        See more information in the `OriginalUrlView.create()` method doc string.
        """
        short_url_path = kwargs.get("shortUrlPath")

        if not self._is_valid(short_url_path):
            return Response("Bad request", status=status.HTTP_400_BAD_REQUEST)

        try:
            original_url_id = short_urls_generator.decode(short_url_path)
        except ValueError:
            return Response("Bad request", status.HTTP_404_NOT_FOUND)

        url = get_object_or_404(URL, pk=original_url_id)
        return HttpResponseRedirect(redirect_to=url.url)

    @staticmethod
    def _is_valid(short_url_path: str) -> bool:
        """Check if all the characters of short url path are the elements of the Alphabet."""
        return all(ch in short_urls_generator.alphabet for ch in short_url_path)
