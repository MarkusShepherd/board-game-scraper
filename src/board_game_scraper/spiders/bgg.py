from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from scrapy.spiders import SitemapSpider

from board_game_scraper.items import CollectionItem, GameItem

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
            bgg_item_type = game.xpath("@type").get()
            if bgg_item_type != "boardgame":
                self.logger.info("Skipping item type <%s>", bgg_item_type)
                continue

            yield GameItem(
                name=game.xpath("name[@type='primary']/@value").get(),
                bgg_id=game.xpath("@id").get(),
                year=game.xpath("yearpublished/@value").get(),
                description=game.xpath("description/text()").get(),
                image_url=game.xpath("image/text()").getall(),  # TODO: <thumbnail>
                scraped_at=datetime.now(timezone.utc),
            )

            for comment in game.xpath("comments/comment"):
                yield CollectionItem(
                    item_id=f"{comment.xpath("@username").get()}:{game.xpath("@id").get()}",
                    bgg_id=game.xpath("@id").get(),
                    bgg_user_name=comment.xpath("@username").get(),
                    bgg_user_rating=comment.xpath("@rating").get(),
                    comment=comment.xpath("@value").get(),
                    scraped_at=datetime.now(timezone.utc),
                )
