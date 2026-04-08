import logging
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
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        raw_page = requests.get(self.url, headers=headers)
        logging.info(f"Fetch page content resulted in {raw_page.status_code} status")
        if raw_page.status_code != 200:
            logging.error(f"Failed to fetch page content from {self.url} with status code {raw_page.status_code}: {raw_page.json()}")
            raise Exception(f"Failed to fetch page content from {self.url} with status code {raw_page.status_code}")
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
        logging.info(f"Page contains {len(lyrics_divs)} lyrics divs")

        for lyrics_div in lyrics_divs:
            lyrics_header = lyrics_div.find('div', attrs={'class': re.compile('LyricsHeader__Container')})
            if lyrics_header:
                lyrics_header.extract()

            line_breaks = lyrics_div.find_all(double_break)
            for lb in line_breaks:
               lb.replace_with(BeautifulSoup("<p>|</p>", 'html.parser'))

            lyrics = lyrics_div.get_text(separator="\n")
            lines = lines + lyrics.split('\n')
            logging.info(f"arsed {len(lines)} lines so far...")

        return lines