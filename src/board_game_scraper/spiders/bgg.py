from __future__ import annotations

import pprint
import re
from typing import TYPE_CHECKING, Any

from attrs import asdict
from scrapy.http import TextResponse
from scrapy.selector.unified import Selector, SelectorList
from scrapy.spiders import SitemapSpider
from scrapy.utils.misc import arg_to_iter

from board_game_scraper.items import CollectionItem, GameItem
from board_game_scraper.loaders import BggGameLoader, CollectionLoader
from board_game_scraper.utils.parsers import parse_float, parse_int

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable

    from scrapy.http import Response


def _value_id(
    items: Selector | SelectorList | Iterable[Selector],
    sep: str = ":",
) -> Generator[str, None, None]:
    for item in arg_to_iter(items):
        assert isinstance(item, Selector)
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
        assert isinstance(item, Selector)
        value = _remove_rank(item.xpath("@friendlyname").get()) or ""
        id_ = item.xpath("@id").get() or ""
        yield f"{value}{sep}{id_}" if id_ else value


class BggSpider(SitemapSpider):
    name = "bgg"
    allowed_domains = ("boardgamegeek.com",)

    sitemap_urls = ("https://boardgamegeek.com/robots.txt",)
    sitemap_follow = (r"/sitemap_geekitems_boardgame_\d+",)
    sitemap_rules = ((r"/xmlapi2/", "parse"),)
    sitemap_alternate_links = True

    def _get_sitemap_body(self, response: Response) -> bytes:
        sitemap_body = super()._get_sitemap_body(response)
        if sitemap_body is not None:
            assert isinstance(sitemap_body, bytes)
            return sitemap_body
        self.logger.warning("YOLO – trying to parse sitemap from <%s>", response.url)
        assert isinstance(response.body, bytes)
        return response.body

    def sitemap_filter(
        self,
        entries: Iterable[dict[str, Any]],
    ) -> Generator[dict[str, Any], None, None]:
        for entry in entries:
            loc = entry.get("loc")
            if not loc:
                continue

            bgg_id = re.search(r"/boardgame/(\d+)", loc)

            if not bgg_id:
                yield entry
                continue

            entry["loc"] = (
                f"https://boardgamegeek.com/xmlapi2/thing?id={bgg_id.group(1)}&type=boardgame&videos=1&stats=1&comments=1&ratingcomments=1&pagesize=100&page=1"
            )
            yield entry

    def parse(  # noqa: PLR0915
        self,
        response: Response,
    ) -> Generator[GameItem | CollectionItem, None, None]:
        """
        @url https://boardgamegeek.com/xmlapi2/thing?id=13,822,36218&type=boardgame&videos=1&stats=1&comments=1&ratingcomments=1&pagesize=100&page=1
        @returns items 303 303
        @returns requests 0 0
        @scrapes name alt_name year description \
            designer artist publisher \
            url image_url video_url \
            min_players max_players min_players_rec max_players_rec \
            min_players_best max_players_best \
            min_age min_age_rec min_time max_time \
            game_type category mechanic cooperative compilation family expansion \
            rank add_rank num_votes avg_rating stddev_rating \
            bayes_rating complexity language_dependency \
            bgg_id scraped_at
        """

        assert isinstance(response, TextResponse)

        for game in response.xpath("/items/item"):
            assert isinstance(game, Selector)
            bgg_item_type = game.xpath("@type").get()
            if bgg_item_type != "boardgame":
                self.logger.info("Skipping item type <%s>", bgg_item_type)
                continue

            gldr = BggGameLoader(response=response, selector=game)

            gldr.add_xpath("bgg_id", "@id")
            gldr.add_xpath("name", "name[@type = 'primary']/@value")
            gldr.add_xpath("alt_name", "name/@value")
            gldr.add_xpath("year", "yearpublished/@value")
            gldr.add_xpath("description", "description/text()")

            gldr.add_value(
                "designer",
                _value_id(game.xpath("link[@type = 'boardgamedesigner']")),
            )
            gldr.add_value(
                "artist",
                _value_id(game.xpath("link[@type = 'boardgameartist']")),
            )
            gldr.add_value(
                "publisher",
                _value_id(game.xpath("link[@type = 'boardgamepublisher']")),
            )

            # TODO: Full URL from sitemap
            bgg_id = gldr.get_output_value("bgg_id")
            gldr.add_value("url", f"https://boardgamegeek.com/boardgame/{bgg_id}")
            gldr.add_xpath("image_url", ("image/text()", "thumbnail/text()"))
            gldr.add_xpath("video_url", "videos/video/@link")

            gldr.add_xpath("min_players", "minplayers/@value")
            gldr.add_xpath("max_players", "maxplayers/@value")
            # TODO: min_players_rec, max_players_rec, min_players_best, max_players_best

            gldr.add_xpath("min_age", "minage/@value")
            gldr.add_xpath("max_age", "maxage/@value")
            # TODO: min_age_rec, max_age_rec

            gldr.add_xpath(
                "min_time",
                ("minplaytime/@value", "playingtime/@value", "maxplaytime/@value"),
            )
            gldr.add_xpath(
                "max_time",
                ("maxplaytime/@value", "playingtime/@value", "minplaytime/@value"),
            )

            gldr.add_value(
                "game_type",
                _value_id_rank(
                    game.xpath("statistics/ratings/ranks/rank[@type = 'family']"),
                ),
            )
            gldr.add_value(
                "category",
                _value_id(game.xpath("link[@type = 'boardgamecategory']")),
            )
            gldr.add_value(
                "mechanic",
                _value_id(game.xpath("link[@type = 'boardgamemechanic']")),
            )
            # look for <link type="boardgamemechanic"
            #              id="2023" value="Co-operative Play" />
            gldr.add_value(
                "cooperative",
                bool(game.xpath("link[@type = 'boardgamemechanic' and @id = '2023']")),
            )
            gldr.add_value(
                "compilation",
                bool(
                    game.xpath(
                        "link[@type = 'boardgamecompilation' and @inbound = 'true']",
                    ),
                ),
            )
            gldr.add_xpath(
                "compilation_of",
                "link[@type = 'boardgamecompilation' and @inbound = 'true']/@id",
            )
            gldr.add_value(
                "family",
                _value_id(game.xpath("link[@type = 'boardgamefamily']")),
            )
            gldr.add_value(
                "expansion",
                _value_id(game.xpath("link[@type = 'boardgameexpansion']")),
            )
            gldr.add_xpath(
                "implementation",
                "link[@type = 'boardgameimplementation' and @inbound = 'true']/@id",
            )
            gldr.add_xpath(
                "integration",
                "link[@type = 'boardgameintegration']/@id",
            )

            gldr.add_xpath(
                "rank",
                "statistics/ratings/ranks/rank[@name = 'boardgame']/@value",
            )
            gldr.add_xpath("num_votes", "statistics/ratings/usersrated/@value")
            gldr.add_xpath("avg_rating", "statistics/ratings/average/@value")
            gldr.add_xpath("stddev_rating", "statistics/ratings/stddev/@value")
            gldr.add_xpath("bayes_rating", "statistics/ratings/bayesaverage/@value")
            gldr.add_xpath("complexity", "statistics/ratings/averageweight/@value")
            # TODO: language_dependency
            # TODO:
            # <owned value="8241" />
            # <trading value="276" />
            # <wanting value="494" />
            # <wishing value="2171" />
            # <numcomments value="2133" />
            # <numweights value="790" />

            for rank in game.xpath('statistics/ratings/ranks/rank[@type = "family"]'):
                # TODO: This should be its own item type
                add_rank = {
                    "game_type": rank.xpath("@name").get(),
                    "game_type_id": parse_int(rank.xpath("@id").get()),
                    "name": _remove_rank(rank.xpath("@friendlyname").get()),
                    "rank": parse_int(rank.xpath("@value").get()),
                    "bayes_rating": parse_float(rank.xpath("@bayesaverage").get()),
                }
                gldr.add_value("add_rank", add_rank)

            game_item = gldr.load_item()
            assert isinstance(game_item, GameItem)
            assert isinstance(game_item.bgg_id, int)
            pprint.pp(asdict(game_item))
            yield game_item

            for comment in game.xpath("comments/comment"):
                user_name = comment.xpath("@username").get()
                item_id = f"{user_name}:{game_item.bgg_id}"
                cldr = CollectionLoader(
                    item=CollectionItem(
                        item_id=item_id,
                        bgg_id=game_item.bgg_id,
                        bgg_user_name=user_name,
                    ),
                    selector=comment,
                )

                cldr.add_xpath("bgg_user_rating", "@rating")
                cldr.add_xpath("comment", "@value")

                yield cldr.load_item()
