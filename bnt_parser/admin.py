from django.contrib import admin

from .models import ExternalSource, Line, Release, Section, Song, Word, Writer

admin.site.register(ExternalSource)
admin.site.register(Release)
admin.site.register(Song)
admin.site.register(Section)
admin.site.register(Writer)
admin.site.register(Line)
admin.site.register(Word)
