import re
import requests
from html.parser import HTMLParser
from bs4 import BeautifulSoup

class GeniusPage:
    def __init__(self, url: str):
        self.url = url
        self.fetchContent()

    # def __repr__(self):
    #     return f"GeniusPage(name={self.name}, url={self.url})"
    #
    # def __str__(self):
    #     return f"{self.name} - {self.url}"

    def fetchContent(self):
        """
        Fetches the content of the Genius page.
        This method should be implemented to retrieve the actual content from the URL.
        """
        raw_page = requests.get(self.url)
        self.page_content = raw_page.content

    def lyrics(self):
        """
        Returns an object containing lyrics broken into sections
        :return:
        """
        page = BeautifulSoup(self.page_content, 'html.parser')
        lyrics_div = page.find('div', attrs={'class': re.compile('Lyrics__Container')})
        lyrics_header = lyrics_div.find('div', attrs={'class': re.compile('LyricsHeader__Container')})
        lyrics_header.clear()
        lines = lyrics_div.get_text(separator="\n")
        lines = lines.split('\n')

        return lines