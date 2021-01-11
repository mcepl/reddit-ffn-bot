# Sink Into Your Eyes site

import logging
import re

from lxml import html

from ffn_bot import site
from ffn_bot.bot_tools import safe_int
from ffn_bot.cache import default_cache
from ffn_bot.metaparse import Metaparser, parser
from ffn_bot.site import Site

__all__ = ["HarryPotterFanfiction"]

https://harrypotterfanfiction.com/viewstory.php?psid=224513

HPFF_LINK_REGEX = re.compile(
    r"http(?:s)?://harrypotterfanfiction\.com/viewstory\.php\?psid=(?P<sid>\d+)",
    re.IGNORECASE)
HPFF_FUNCTION = "linksiye"
HPFF_SEARCH_QUERY = "http://harrypotterfanfiction.com/viewstory.php?psid=%s"

HPFF_AUTHOR_URL = '//html/body/main/section[1]/article/div/h2/i/a//@href'
HPFF_SUMMARY_AND_META = '//html/body/main/section[2]/article/div[2]//text()'
HPFF_TITLE_AUTHOR_NAME = '//html/body/main/section[1]/article/div/h2/i/a//text()'


class HPFFMetadata(Metaparser):

    @parser
    @staticmethod
    def parse_metadata(id, tree):
        summary_and_meta = ' '.join(tree.xpath(HPFF_SUMMARY_AND_META))
        stats = summary_and_meta
        stats = re.sub("Story Total: ", "",stats.replace("Awards:  View Trophy Room",""))
        if "Story is Complete" in stats:
            stats = re.sub("Story is Complete","Status: Complete", stats)
        else:
            stats = stats + "Status: In Progress"
        stats = stats.split("\n")
        stats = [x for x in stats if x.strip()]
        for l in stats:
            individual_stat = tuple(p.strip() for p in l.split(":", 2))
            if individual_stat[0]!="Summary": # Don't return the summary
                if individual_stat[0]=="Reviews":
                    if individual_stat[1]: # If the reviews stat is not present, don't return it
                        yield individual_stat
                else:
                    yield individual_stat



    @parser
    @staticmethod
    def ID(id, tree):
        return id


class HarryPotterFanfiction(Site):

    def __init__(self, regex=HPFF_FUNCTION, name=None):
        super(HarryPotterFanfiction, self).__init__(regex, name)

    def from_requests(self, requests, context):
        _pitem = []
        item = _pitem
        for request in requests:
            try:
                item = self.process(request, context)
            except Exception as e:
                continue

            if item is not None:
                yield item

    def process(self, request, context):
        try:
            link = self.find_link(request, context)
        except IOError as e:
            logging.error("FF not found: %s" % request)
            return

        if link is None:
            return

        return self.generate_response(link, context)

    @staticmethod
    def id_to_url(id):
        return "http://harrypotterfanfiction.com/viewstory.php?psid=%s" % id

    def find_link(self, request, context):
        # Find link by ID.
        id = safe_int(request)
        if id is not None:
            return self.id_to_url(id)
        # Filter out direct links.
        match = HPFF_LINK_REGEX.match(request)
        if match is not None:
            return request

        return default_cache.search(HPFF_SEARCH_QUERY % id)

    def generate_response(self, link, context):
        assert link is not None
        return Story(link, context)

    def extract_direct_links(self, body, context):
        return (
            self.generate_response(self.id_to_url(safe_int(id)), context)
            for id in HPFF_LINK_REGEX.findall(body)
        )

    def get_story(self, query):
        return Story(self.find_link(query, set()))


class Story(site.Story):

    def __init__(self, url, context=None):
        super(Story, self).__init__(context)
        self.url = url
        self.raw_stats = []

        self.stats = ""
        self.title = ""
        self.author = ""
        self.authorlink = ""
        self.summary = ""
        self.summary_and_meta = ""

    def get_url(self):
        return HarryPotterFanfiction.id_to_url(
            str(HPFF_LINK_REGEX.match(self.url).groupdict()["sid"])
        )

    def parse_html(self):
        self.tree = tree = html.fromstring(default_cache.get_page(self.url))

        self.summary_and_meta = ' '.join(tree.xpath(HPFF_SUMMARY_AND_META))
        self.summary = ''.join(
            re.findall(
                'Summary: (.*?)(?=Hitcount:)',
                self.summary_and_meta,
                re.DOTALL
            )
        ).replace("\n", " ").strip()
        self.stats = HPFFMetadata(
            str(HPFF_LINK_REGEX.match(self.url).groupdict()["sid"]),
            self.tree

        )
        self.title = tree.xpath(HPFF_TITLE_AUTHOR_NAME)[0]
        self.author = tree.xpath(HPFF_TITLE_AUTHOR_NAME)[2]
        self.authorlink = 'http://harrypotterfanfiction.com/' + \
                          tree.xpath(HPFF_AUTHOR_URL)[0]

    def get_site(self):
        return "Harry Potter Fanfiction", "http://harrypotterfanfiction.com"
