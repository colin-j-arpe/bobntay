import logging
import re

import requests
from bs4 import BeautifulSoup

NON_MUSIC_TAG = re.compile(r"/tags/non-music")


class GeniusPage:
    def __init__(self, url: str, html: bytes | None = None):
        self.url = url
        if html is not None:
            self.page_content = html
        else:
            self.fetchContent()

        self._soup: BeautifulSoup | None = None
        self._lyrics: list[str] | None = None

    @property
    def soup(self) -> BeautifulSoup:
        """
        The parsed page, built on first use and then reused.

        Pages run to hundreds of kilobytes, so parsing is the expensive part of
        reading a tag. Parsing lazily rather than in __init__ keeps construction
        cheap and avoids the work entirely for callers that only want the URL.
        """
        if self._soup is None:
            self._soup = BeautifulSoup(self.page_content, "html.parser")
        return self._soup

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
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"  # noqa: E501
        }
        raw_page = requests.get(self.url, headers=headers)
        logging.info(f"Fetch page content resulted in {raw_page.status_code} status")
        if raw_page.status_code != 200:
            logging.error(
                "Failed to fetch page content from %s with status code %s: %s",
                self.url,
                raw_page.status_code,
                raw_page.text,
            )
            raise Exception(
                f"Failed to fetch page content from {self.url}"
                f" with status code {raw_page.status_code}"
            )
        self.page_content = raw_page.content

    def is_non_music(self) -> bool:
        """
        Returns True if the page is tagged Non-Music.

        Genius applies this tag to tour setlists, release calendars, liner notes,
        speeches and similar pages that are not songs. Matched on the href because
        the class name carries a build hash (SongTags__Tag-sc-93a3a73a-3) that
        changes whenever Genius rebuilds its front end.

        Safe to call before or after lyrics(): the tag links live outside the
        lyrics containers, which is all lyrics() mutates.
        """
        return self.soup.find("a", href=NON_MUSIC_TAG) is not None

    def lyrics(self):
        """
        Returns an object containing lyrics broken into sections
        :return:
        """
        # The parse below is destructive: it extracts headers and replaces double
        # line breaks in the shared soup. Those edits happen to be idempotent, so a
        # second pass returns the same lines (pinned by
        # test_lyrics_stable_across_calls) — but it re-walks the whole tree to get
        # there, and would silently start returning something else if the parse
        # ever gained a non-idempotent step. Memoised on both counts.
        if self._lyrics is not None:
            return self._lyrics

        page = self.soup

        def double_break(tag):
            return tag.name == "br" and tag.next_element.name == "br"

        lines = []
        lyrics_divs = page.find_all("div", attrs={"class": re.compile("Lyrics__Container")})
        logging.info(f"Page contains {len(lyrics_divs)} lyrics divs")

        for lyrics_div in lyrics_divs:
            lyrics_header = lyrics_div.find(
                "div", attrs={"class": re.compile("LyricsHeader__Container")}
            )
            if lyrics_header:
                lyrics_header.extract()

            line_breaks = lyrics_div.find_all(double_break)
            for lb in line_breaks:
                lb.replace_with(BeautifulSoup("<p>|</p>", "html.parser"))

            lyrics = lyrics_div.get_text(separator="\n")
            lines = lines + lyrics.split("\n")
            logging.info(f"arsed {len(lines)} lines so far...")

        self._lyrics = lines
        return lines
