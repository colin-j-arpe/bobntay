from django.core.management.base import BaseCommand

from bnt_parser.cron import add_song


class Command(BaseCommand):
    help = 'Select the next unprocessed song and save it to the database.'

    def handle(self, *args, **options):
        add_song()
