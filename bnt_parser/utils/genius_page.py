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

        def double_break(tag):
            return tag.name == 'br' and tag.next_element.name == 'br'
        lines = []
        lyrics_divs = page.find_all('div', attrs={'class': re.compile('Lyrics__Container')})

        for lyrics_div in lyrics_divs:
            lyrics_header = lyrics_div.find('div', attrs={'class': re.compile('LyricsHeader__Container')})
            if lyrics_header:
                lyrics_header.extract()

            line_breaks = lyrics_div.find_all(double_break)
            for lb in line_breaks:
               lb.replace_with(BeautifulSoup("<p>|</p>", 'html.parser'))

            lyrics = lyrics_div.get_text(separator="\n")
            lines = lines + lyrics.split('\n')

        return lines