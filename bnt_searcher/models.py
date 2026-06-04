from django.db import models


class WordVariantLookup(models.Model):
    headword = models.CharField(max_length=63, unique=True, blank=False)
    fetched_at = models.DateTimeField(blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.headword

    class Meta:
        verbose_name = "Word Variant Lookup"
        verbose_name_plural = "Word Variant Lookups"


class WordVariant(models.Model):
    lookup = models.ForeignKey(WordVariantLookup, on_delete=models.CASCADE, related_name='variants', blank=False)
    text = models.CharField(max_length=63, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.text

    class Meta:
        verbose_name = "Word Variant"
        verbose_name_plural = "Word Variants"
        constraints = [
            models.UniqueConstraint(fields=['lookup', 'text'], name='unique_variant_per_lookup'),
        ]


class WordVariantAlias(models.Model):
    searched_term = models.CharField(max_length=63, unique=True, blank=False)
    lookup = models.ForeignKey(
        WordVariantLookup, on_delete=models.CASCADE, related_name='aliases', blank=False
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.searched_term

    class Meta:
        verbose_name = "Word Variant Alias"
        verbose_name_plural = "Word Variant Aliases"
