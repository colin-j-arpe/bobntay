from django.db import models
from django_enum import EnumField


class ExternalSource(models.Model):
    """
    Model to represent an external source of lyrics.
    """

    class SourceEnum(models.TextChoices):
        GENIUS = "GENIUS", "Genius"
        MUSIXMATCH = "MUSIXMATCH", "Musixmatch"

    source = EnumField(SourceEnum, null=False, blank=False)
    external_id = models.IntegerField(null=True, blank=False)
    endpoint = models.CharField(max_length=255, null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "External Source"
        verbose_name_plural = "External Sources"

    def __str__(self):
        return self.endpoint


class RejectedTrack(models.Model):
    """
    Model to record a track that was inspected and deliberately not stored.

    Kept deliberately separate from ExternalSource. Song, Writer and Release each
    hold a OneToOneField to ExternalSource, so a rejection recorded there would be
    an orphan row and would make ExternalSourceTable.song_exists() report unsaved
    songs as already saved.

    Without this record, a track rejected after the API search loop has finished
    can never be skipped: nothing is saved, so song_exists() keeps returning False
    and the same track is served forever.
    """

    class ReasonEnum(models.TextChoices):
        TRANSLATION = "TRANSLATION", "Translation of another song"
        NON_MUSIC = "NON_MUSIC", "Tagged Non-Music"
        NO_LYRICS = "NO_LYRICS", "No lyrics found on page"
        PAGE_GONE = "PAGE_GONE", "Genius page no longer exists"

    source = EnumField(ExternalSource.SourceEnum, null=False, blank=False)
    external_id = models.IntegerField(null=True, blank=False)
    endpoint = models.CharField(max_length=255, null=False, blank=False)
    reason = EnumField(ReasonEnum, null=False, blank=False)
    # Title and artist are denormalised copies held purely so rejections can be
    # audited without a second API call. Nothing reads them.
    title = models.CharField(max_length=255, blank=True)
    artist = models.CharField(max_length=127, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Rejected Track"
        verbose_name_plural = "Rejected Tracks"
        # No separate Index here: the unique constraint already builds a btree on
        # exactly (source, external_id), which is the only way this table is
        # queried, so an explicit index would just be a second copy to maintain.
        constraints = [
            models.UniqueConstraint(
                fields=["source", "external_id"],
                name="unique_rejected_track",
            ),
        ]

    def __str__(self):
        return f'"{self.title}" by {self.artist} rejected: {self.reason}'


class Release(models.Model):
    """
    Model to represent a release containing one or more songs.
    """

    artist = models.CharField(max_length=127, null=False, blank=False)
    title = models.CharField(max_length=255, null=False, blank=False)
    release_date = models.DateField(null=True, blank=True)
    label = models.CharField(max_length=63, null=True, blank=False)  # noqa: DJ001
    external_source = models.OneToOneField(ExternalSource, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Release"
        verbose_name_plural = "Releases"

    def __str__(self):
        return f'"{self.title}" by {self.artist}'


class Song(models.Model):
    """
    Model to represent a song with lyrics.
    """

    title = models.CharField(max_length=255, blank=False)
    artist = models.CharField(max_length=127, blank=False)
    release = models.ForeignKey(Release, on_delete=models.CASCADE, related_name="songs", null=True)
    external_source = models.OneToOneField(ExternalSource, on_delete=models.CASCADE, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Song"
        verbose_name_plural = "Songs"

    def __str__(self):
        return f'"{self.title}" by {self.artist}'


class Section(models.Model):
    """
    Model to represent a section of lyrics within a song.
    """

    class SectionTypeEnum(models.TextChoices):
        INTRO = "INTRO", "Intro"
        VERSE = "VERSE", "Verse"
        PRECHORUS = "PRECHORUS", "Pre-Chorus"
        CHORUS = "CHORUS", "Chorus"
        POSTCHORUS = "POSTCHORUS", "Post-Chorus"
        BRIDGE = "BRIDGE", "Bridge"
        BREAKDOWN = "BREAKDOWN", "Breakdown"
        SPOKEN = "SPOKEN", "Spoken"
        CODA = "CODA", "Coda"
        OUTRO = "OUTRO", "Outro"
        OTHER = "OTHER", "Other"

    song = models.ForeignKey(Song, on_delete=models.CASCADE, related_name="sections")
    order = models.PositiveIntegerField(blank=False)
    type = EnumField(SectionTypeEnum, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Section"
        verbose_name_plural = "Sections"

    def __str__(self):
        return f'Section {self.order} ({self.type}) of "{self.song.title}"'

    def get_type_display(self) -> str:
        return self.SectionTypeEnum(self.type)


class Writer(models.Model):
    """
    Model to represent a writer of a song.
    """

    name = models.CharField(max_length=127, blank=False)
    external_source = models.OneToOneField(ExternalSource, on_delete=models.CASCADE, blank=False)
    songs = models.ManyToManyField(Song, related_name="writers", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Writer"
        verbose_name_plural = "Writers"

    def __str__(self):
        return self.name


class Line(models.Model):
    """
    Model to represent a line of lyrics within a section.
    """

    lyrics = models.TextField(blank=False)
    order = models.PositiveIntegerField(blank=False)
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="lines")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Line"
        verbose_name_plural = "Lines"
        ordering = [
            "section__order",
            "order",
        ]  # Ensure lines are ordered by section and then by their order

    def __str__(self):
        return self.lyrics


class Word(models.Model):
    """
    Model to represent a word used in lyrics.
    """

    text = models.CharField(max_length=63, blank=False)
    line = models.ManyToManyField(Line, related_name="words", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Word"
        verbose_name_plural = "Words"
        ordering = ["text"]

    def __str__(self):
        return self.text
