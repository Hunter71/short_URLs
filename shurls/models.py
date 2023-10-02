from django.db import models


class URL(models.Model):
    id = models.AutoField(primary_key=True)
    # The uniqueness of the url won't be enforced, as short URL generation is based on `id` rather than `url` itself.
    # Thus, it is possible to have duplicated original URLs with each duplicate having different short URL.
    url = models.URLField(unique=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.url
