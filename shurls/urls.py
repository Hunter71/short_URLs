from django.urls import path

from shurls.views import OriginalUrlView, ShortUrlsView

urlpatterns = [
    path("", OriginalUrlView.as_view(), name="index"),
    path("<str:shortUrlPath>", ShortUrlsView.as_view(), name="short_url"),
]
