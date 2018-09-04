# -*- coding: utf-8 -*-

''' Spielen.de spider '''

import re

from scrapy import Spider

from ..items import GameItem
from ..loaders import GameLoader


def _parse_interval(text):
    match = re.match(r'^.*?(\d+)(\s*-\s*(\d+))?.*$', text)
    if match:
        return match.group(1), match.group(3)
    return None, None


def _parse_int(text):
    match = re.match(r'^.*?(\d+).*$', text)
    if match:
        return match.group(1)
    return None


class SpielenSpider(Spider):
    ''' Spielen.de spider '''

    name = 'spielen'
    allowed_domains = ['spielen.de']
    start_urls = ['https://gesellschaftsspiele.spielen.de/alle-brettspiele/']
    item_classes = (GameItem,)

    def parse(self, response):
        '''
        @url https://gesellschaftsspiele.spielen.de/alle-brettspiele/
        @returns items 0 0
        @returns requests 19 19
        '''

        next_page = (response.css('.listPagination a.glyphicon-step-forward::attr(href)')
                     .extract_first())
        if next_page:
            yield response.follow(next_page, callback=self.parse)

        for game in response.css('div.listItem'):
            url = game.css('h3 a::attr(href)').extract_first()
            if url:
                yield response.follow(url, callback=self.parse_game)

    # pylint: disable=no-self-use
    def parse_game(self, response):
        '''
        @url https://gesellschaftsspiele.spielen.de/alle-brettspiele/catan-das-spiel/
        @returns items 1 1
        @returns requests 0 0
        @scrapes name year description designer artist publisher \
                 url image_url video_url \
                 min_players max_players min_age min_time max_time family \
                 num_votes avg_rating worst_rating best_rating \
                 complexity easiest_complexity hardest_complexity
        '''

        game = response.css('div.fullBox')

        ldr = GameLoader(
            item=GameItem(
                worst_rating=1,
                best_rating=5,
                easiest_complexity=1,
                hardest_complexity=5,
            ),
            selector=game,
            response=response,
        )

        ldr.add_css('name', 'h2')
        ldr.add_xpath('year', './/div[b = "Erscheinungsjahr:"]/following-sibling::div//text()')
        ldr.add_xpath('description', './/h2/following-sibling::text()')

        ldr.add_xpath(
            'designer', './/div[b = "Autor:" or b = "Autoren:"]/following-sibling::div//text()')
        ldr.add_xpath(
            'artist',
            './/div[b = "Illustrator:" or b = "Illustratoren:"]/following-sibling::div//text()')
        ldr.add_xpath(
            'publisher', './/div[b = "Verlag:" or b = "Verlage:"]/following-sibling::div//a')

        ldr.add_value('url', response.url)

        images = [
            game.xpath('(.//img)[1]/@data-src').extract_first(),
            game.xpath('(.//a[img])[1]/@href').extract_first(),
        ] + game.css('div.screenshotlist img::attr(data-large-src)').extract()
        ldr.add_value('image_url', (response.urljoin(i) for i in images if i))

        videos = (
            game.css('iframe::attr(src)').extract()
            + game.css('iframe::attr(data-src)').extract())
        ldr.add_value('video_url', (response.urljoin(v) for v in videos if v))

        players = game.xpath(
            './/div[b = "Spieler:"]/following-sibling::div/text()').extract_first()
        # TODO parse 'besonders gut mit 4 Spielern'
        min_players, max_players = _parse_interval(players) if players else (None, None)
        ldr.add_value('min_players', min_players)
        ldr.add_value('max_players', max_players)

        age = game.xpath('.//div[b = "Alter:"]/following-sibling::div/text()').extract_first()
        ldr.add_value('min_age', _parse_int(age) if age else None)

        time = game.xpath('.//div[b = "Dauer:"]/following-sibling::div/text()').extract_first()
        min_time, max_time = _parse_interval(time) if time else (None, None)
        ldr.add_value('min_time', min_time)
        ldr.add_value('max_time', max_time)

        ldr.add_xpath(
            'family',
            './/div[b = "Spielfamilie:" or b = "Spielfamilien:"]/following-sibling::div//text()')

        ldr.add_css('num_votes', 'span.votes')
        ldr.add_css('avg_rating', 'span.average')

        complexity = game.xpath(
            './/div[. = "Komplexität:"]/following-sibling::div'
            '/span[following-sibling::span[contains(@class, "red")]]')
        complexity = len(complexity) + 1
        ldr.add_value('complexity', complexity)

        return ldr.load_item()
