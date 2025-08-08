from django.contrib import admin
from .models import ExternalSource, Release, Song, Section, Writer, Line, Word

admin.site.register(ExternalSource)
admin.site.register(Release)
admin.site.register(Song)
admin.site.register(Section)
admin.site.register(Writer)
admin.site.register(Line)
admin.site.register(Word)
