from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from scrapy import Selector
from scrapy.spiders import SitemapSpider

from board_game_scraper.items import CollectionItem, GameItem
from board_game_scraper.loaders import CollectionLoader, GameLoader

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable

    from scrapy.http import Response


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
                f"https://boardgamegeek.com/xmlapi2/thing?id={bgg_id.group(1)}&type=boardgame&versions=1&videos=1&stats=1&comments=1&ratingcomments=1&pagesize=100&page=1"
            )
            yield entry

    def parse(
        self,
        response: Response,
    ) -> Generator[GameItem | CollectionItem, None, None]:
        for game in response.xpath("/items/item"):
            assert isinstance(game, Selector)
            bgg_item_type = game.xpath("@type").get()
            if bgg_item_type != "boardgame":
                self.logger.info("Skipping item type <%s>", bgg_item_type)
                continue

            # name = game.xpath("name[@type='primary']/@value").get()
            # bgg_id = int(game.xpath("@id").get())  # TODO: Safe parsing
            gldr = GameLoader(
                # item=GameItem(name=name, bgg_id=bgg_id),
                selector=game,
            )

            gldr.add_xpath("name", "name[@type='primary']/@value")
            gldr.add_xpath("bgg_id", "@id")
            gldr.add_xpath("year", "yearpublished/@value")
            gldr.add_xpath("description", "description/text()")
            gldr.add_xpath("image_url", "image/text()")
            gldr.add_xpath("image_url", "thumbnail/text()")

            game_item = gldr.load_item()
            assert isinstance(game_item, GameItem)
            assert isinstance(game_item.bgg_id, int)
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
