from __future__ import annotations

import re
import warnings
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import urlencode

from more_itertools import chunked
from scrapy.http import Request, TextResponse
from scrapy.selector.unified import Selector, SelectorList
from scrapy.spiders import SitemapSpider
from scrapy.utils.misc import arg_to_iter

from board_game_scraper.items import CollectionItem, GameItem, RankingItem
from board_game_scraper.loaders import BggGameLoader, CollectionLoader, RankingLoader
from board_game_scraper.utils.parsers import parse_int

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable

    from scrapy.http import Response


def _value_id(
    items: Selector | SelectorList | Iterable[Selector],
    sep: str = ":",
) -> Generator[str, None, None]:
    for item in arg_to_iter(items):
        item = cast(Selector, item)
        value = item.xpath("@value").get() or ""
        id_ = item.xpath("@id").get() or ""
        yield f"{value}{sep}{id_}" if id_ else value


def _remove_rank(value: str | None) -> str | None:
    return (
        value[:-5]
        if isinstance(value, str) and value.lower().endswith(" rank")
        else value
    )


def _value_id_rank(
    items: Selector | SelectorList | Iterable[Selector],
    sep: str = ":",
) -> Generator[str, None, None]:
    for item in arg_to_iter(items):
        item = cast(Selector, item)
        value = _remove_rank(item.xpath("@friendlyname").get()) or ""
        id_ = item.xpath("@id").get() or ""
        yield f"{value}{sep}{id_}" if id_ else value


class BggSpider(SitemapSpider):
    name = "bgg"
    allowed_domains = ("boardgamegeek.com",)

    # https://boardgamegeek.com/wiki/page/BGG_XML_API2
    bgg_xml_api_url = "https://boardgamegeek.com/xmlapi2"
    bgg_id_regex = re.compile(r"/boardgame(compilation|implementation)?/(\d+)")
    request_page_size = 100
    game_request_batch_size = 20

    # Start URLs for sitemap crawling
    sitemap_urls = ("https://boardgamegeek.com/robots.txt",)
    # Recursively follow sitemapindex locs if they match any of these patterns
    sitemap_follow = (r"/sitemap_geekitems_boardgame(compilation|implementation)?_\d+",)
    # Parse sitemap urlset locs with these callback rules
    sitemap_rules = ((bgg_id_regex, "parse_games"),)
    # Parse alternate links in sitemap locs
    sitemap_alternate_links = True

    def start_requests(self) -> Iterable[Request]:
        # TODO: Add other ways to create game and user requests
        return super().start_requests()

    def _get_sitemap_body(self, response: Response) -> bytes:
        sitemap_body = super()._get_sitemap_body(response)
        if sitemap_body is not None:
            return sitemap_body
        self.logger.warning("YOLO – trying to parse sitemap from <%s>", response.url)
        return response.body

    def _parse_sitemap(self, response: Response) -> Generator[Request, None, None]:
        """
        @url https://boardgamegeek.com/sitemap_geekitems_boardgame_1
        @returns items 0 0
        @returns requests 500 500
        """

        bgg_ids: set[int] = set()

        for request in super()._parse_sitemap(response):
            bgg_id_match = self.bgg_id_regex.search(request.url)
            bgg_id = parse_int(bgg_id_match.group(2)) if bgg_id_match else None
            if bgg_id:
                bgg_ids.add(bgg_id)
            else:
                yield request

        yield from self.game_requests(bgg_ids)

    def game_requests(
        self,
        bgg_ids: Iterable[int],
        page: int = 1,
        priority: int = 0,
        **kwargs: Any,
    ) -> Generator[Request, None, None]:
        bgg_ids = frozenset(bgg_ids)

        if page == 1:
            bgg_ids = [bgg_id for bgg_id in bgg_ids if not self.has_seen_bgg_id(bgg_id)]

        if not bgg_ids:
            return

        for bgg_ids_chunk in chunked(sorted(bgg_ids), self.game_request_batch_size):
            bgg_ids_str = ",".join(map(str, bgg_ids_chunk))
            url = self.api_url(
                action="thing",
                id=bgg_ids_str,
                type="boardgame",
                videos="1",
                stats="1" if page == 1 else None,
                ratingcomments="1" if page == 1 else None,
                page=str(page),
            )

            request = Request(
                url=url,
                callback=self.parse_games,  # type: ignore[arg-type]
                priority=priority,
            )
            request.meta["page"] = page
            request.meta.update(kwargs)

            yield request

    def has_seen_bgg_id(self, bgg_id: int) -> bool:
        state = getattr(self, "state", None)
        if state is None or not isinstance(state, dict):
            warnings.warn("No spider state found", stacklevel=2)
            return False

        bgg_ids_seen = cast(set[int], state.setdefault("bgg_ids_seen", set()))
        seen = bgg_id in bgg_ids_seen
        bgg_ids_seen.add(bgg_id)

        return seen

    def api_url(self, action: str, **kwargs: str | None) -> str:
        kwargs["pagesize"] = str(self.request_page_size)
        params = ((k, v) for k, v in kwargs.items() if k and v is not None)
        return f"{self.bgg_xml_api_url}/{action}?{urlencode(sorted(params))}"

    def parse_games(
        self,
        response: Response,
    ) -> Generator[GameItem | CollectionItem, None, None]:
        """
        @url https://boardgamegeek.com/xmlapi2/thing?id=13,822,36218&type=boardgame&videos=1&stats=1&comments=1&ratingcomments=1&pagesize=100&page=1
        @returns items 303 303
        @returns requests 0 0
        @scrapes bgg_id scraped_at
        """

        response = cast(TextResponse, response)

        for game in response.xpath("/items/item"):
            game = cast(Selector, game)
            bgg_item_type = game.xpath("@type").get()
            if bgg_item_type != "boardgame":
                self.logger.info("Skipping item type <%s>", bgg_item_type)
                continue

            game_item = self.extract_game_item(response=response, game=game)
            yield game_item

            for comment in game.xpath("comments/comment"):
                yield self.extract_collection_item(
                    response=response,
                    comment=comment,
                    bgg_id=cast(int, game_item.bgg_id),
                )

    def extract_game_item(self, *, response: TextResponse, game: Selector) -> GameItem:
        ldr = BggGameLoader(response=response, selector=game)

        ldr.add_xpath("bgg_id", "@id")
        ldr.add_xpath("name", "name[@type = 'primary']/@value")
        ldr.add_xpath("alt_name", "name/@value")
        ldr.add_xpath("year", "yearpublished/@value")
        ldr.add_xpath("description", "description/text()")

        ldr.add_value(
            "designer",
            _value_id(game.xpath("link[@type = 'boardgamedesigner']")),
        )
        ldr.add_value(
            "artist",
            _value_id(game.xpath("link[@type = 'boardgameartist']")),
        )
        ldr.add_value(
            "publisher",
            _value_id(game.xpath("link[@type = 'boardgamepublisher']")),
        )

        bgg_id = ldr.get_output_value("bgg_id")
        ldr.add_value("url", f"/boardgame/{bgg_id}/")
        ldr.add_xpath("image_url", ("image/text()", "thumbnail/text()"))
        ldr.add_xpath("video_url", "videos/video/@link")

        ldr.add_xpath("min_players", "minplayers/@value")
        ldr.add_xpath("max_players", "maxplayers/@value")
        # TODO: min_players_rec, max_players_rec, min_players_best, max_players_best

        ldr.add_xpath("min_age", "minage/@value")
        ldr.add_xpath("max_age", "maxage/@value")
        # TODO: min_age_rec, max_age_rec

        ldr.add_xpath(
            "min_time",
            ("minplaytime/@value", "playingtime/@value", "maxplaytime/@value"),
        )
        ldr.add_xpath(
            "max_time",
            ("maxplaytime/@value", "playingtime/@value", "minplaytime/@value"),
        )

        ldr.add_value(
            "game_type",
            _value_id_rank(
                game.xpath("statistics/ratings/ranks/rank[@type = 'family']"),
            ),
        )
        ldr.add_value(
            "category",
            _value_id(game.xpath("link[@type = 'boardgamecategory']")),
        )
        ldr.add_value(
            "mechanic",
            _value_id(game.xpath("link[@type = 'boardgamemechanic']")),
        )
        # look for <link type="boardgamemechanic" id="2023" value="Co-operative Play" />
        ldr.add_value(
            "cooperative",
            bool(game.xpath("link[@type = 'boardgamemechanic' and @id = '2023']")),
        )
        ldr.add_value(
            "compilation",
            bool(
                game.xpath(
                    "link[@type = 'boardgamecompilation' and @inbound = 'true']",
                ),
            ),
        )
        ldr.add_xpath(
            "compilation_of",
            "link[@type = 'boardgamecompilation' and @inbound = 'true']/@id",
        )
        ldr.add_value(
            "family",
            _value_id(game.xpath("link[@type = 'boardgamefamily']")),
        )
        ldr.add_value(
            "expansion",
            _value_id(game.xpath("link[@type = 'boardgameexpansion']")),
        )
        ldr.add_xpath(
            "implementation",
            "link[@type = 'boardgameimplementation' and @inbound = 'true']/@id",
        )
        ldr.add_xpath(
            "integration",
            "link[@type = 'boardgameintegration']/@id",
        )

        ldr.add_xpath(
            "rank",
            "statistics/ratings/ranks/rank[@name = 'boardgame']/@value",
        )
        ldr.add_xpath("num_votes", "statistics/ratings/usersrated/@value")
        ldr.add_xpath("avg_rating", "statistics/ratings/average/@value")
        ldr.add_xpath("stddev_rating", "statistics/ratings/stddev/@value")
        ldr.add_xpath("bayes_rating", "statistics/ratings/bayesaverage/@value")
        ldr.add_xpath("complexity", "statistics/ratings/averageweight/@value")
        # TODO: language_dependency
        # TODO:
        # <owned value="8241" />
        # <trading value="276" />
        # <wanting value="494" />
        # <wishing value="2171" />
        # <numcomments value="2133" />
        # <numweights value="790" />

        for rank in game.xpath("statistics/ratings/ranks/rank[@type = 'family']"):
            ranking_item = self.extract_ranking_item(response=response, rank=rank)
            ldr.add_value("add_rank", ranking_item)

        return cast(GameItem, ldr.load_item())

    def extract_ranking_item(
        self,
        *,
        response: TextResponse,
        rank: Selector,
    ) -> RankingItem:
        ldr = RankingLoader(response=response, selector=rank)
        ldr.add_xpath("ranking_type", "@name")
        ldr.add_xpath("ranking_id", "@id")
        ldr.add_xpath("rank", "@value")
        ldr.add_xpath("bayes_rating", "@bayesaverage")
        return cast(RankingItem, ldr.load_item())

    def extract_collection_item(
        self,
        *,
        response: TextResponse,
        comment: Selector,
        bgg_id: int,
    ) -> CollectionItem:
        ldr = CollectionLoader(response=response, selector=comment)
        ldr.add_value("bgg_id", bgg_id)
        ldr.add_xpath("bgg_user_name", "@username")
        ldr.add_xpath("bgg_user_rating", "@rating")
        ldr.add_xpath("comment", "@value")
        return cast(CollectionItem, ldr.load_item())
