from django.db import models
from django_enum import EnumField

class ExternalSource(models.Model):
    """
    Model to represent an external source of lyrics.
    """
    class SourceEnum(models.TextChoices):
        GENIUS = 'GENIUS', 'Genius'
        MUSIXMATCH = 'MUSIXMATCH', 'Musixmatch'

    source = EnumField(SourceEnum, null=False, blank=False)
    external_id = models.IntegerField(null=True, blank=False)
    endpoint = models.CharField(max_length=255, null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.endpoint

    class Meta:
        verbose_name = "External Source"
        verbose_name_plural = "External Sources"

class Release(models.Model):
    """
    Model to represent a release containing one or more songs.
    """
    artist = models.CharField(max_length=127, null=False, blank=False)
    title = models.CharField(max_length=255, null=False, blank=False)
    release_date = models.DateField(null=True, blank=True)
    label = models.CharField(max_length=63, null=True, blank=False)
    external_source = models.OneToOneField(ExternalSource, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"\"{self.title}\" by {self.artist}"

    class Meta:
        verbose_name = "Release"
        verbose_name_plural = "Releases"

class Song(models.Model):
    """
    Model to represent a song with lyrics.
    """
    title = models.CharField(max_length=255, blank=False)
    artist = models.CharField(max_length=127, blank=False)
    release = models.ForeignKey(Release, on_delete=models.CASCADE, related_name='songs', null=True)
    external_source = models.OneToOneField(ExternalSource, on_delete=models.CASCADE, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"\"{self.title}\" by {self.artist}"

    class Meta:
        verbose_name = "Song"
        verbose_name_plural = "Songs"

class Section(models.Model):
    """
    Model to represent a section of lyrics within a song.
    """
    class SectionTypeEnum(models.TextChoices):
        INTRO = 'INTRO', 'Intro'
        VERSE = 'VERSE', 'Verse'
        PRECHORUS = 'PRECHORUS', 'Pre-Chorus'
        CHORUS = 'CHORUS', 'Chorus'
        POSTCHORUS = 'POSTCHORUS', 'Post-Chorus'
        BRIDGE = 'BRIDGE', 'Bridge'
        BREAKDOWN = 'BREAKDOWN', 'Breakdown'
        SPOKEN = 'SPOKEN', 'Spoken'
        CODA = 'CODA', 'Coda'
        OUTRO = 'OUTRO', 'Outro'
        OTHER = 'OTHER', 'Other'

    song = models.ForeignKey(Song, on_delete=models.CASCADE, related_name='sections')
    order = models.PositiveIntegerField(blank=False)
    type = EnumField(SectionTypeEnum, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Section {self.order} ({self.type}) of \"{self.song.title}\""

    def get_type_display(self) -> str:
        return self.SectionTypeEnum(self.type)

    class Meta:
        verbose_name = "Section"
        verbose_name_plural = "Sections"

class Writer(models.Model):
    """
    Model to represent a writer of a song.
    """
    name = models.CharField(max_length=127, blank=False)
    external_source = models.OneToOneField(ExternalSource, on_delete=models.CASCADE, blank=False)
    songs = models.ManyToManyField(Song, related_name='writers', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Writer"
        verbose_name_plural = "Writers"

class Line(models.Model):
    """
    Model to represent a line of lyrics within a section.
    """
    lyrics = models.TextField(blank=False)
    order = models.PositiveIntegerField(blank=False)
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='lines')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.lyrics

    class Meta:
        verbose_name = "Line"
        verbose_name_plural = "Lines"
        ordering = ['section__order', 'order']  # Ensure lines are ordered by section and then by their order

class Word(models.Model):
    """
    Model to represent a word used in lyrics.
    """
    text = models.CharField(max_length=63, blank=False)
    line = models.ManyToManyField(Line, related_name='words', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.text

    class Meta:
        verbose_name = "Word"
        verbose_name_plural = "Words"
        ordering = ['text']