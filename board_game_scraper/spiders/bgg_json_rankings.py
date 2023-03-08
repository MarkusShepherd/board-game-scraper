"""BoardGameGeek JSON spider."""

import csv
import os
from datetime import timezone
from io import StringIO
from pathlib import Path
from typing import Optional

from pytility import parse_date, parse_int
from scrapy import Request, Spider

from ..items import GameItem
from ..utils import extract_query_param, json_from_response, now


class BggJsonSpider(Spider):
    """BoardGameGeek JSON spider."""

    name = "bgg_json_rankings"
    allowed_domains = ("geekdo.com",)
    start_urls = (
        (
            Path(__file__).parent.parent.parent.parent
            / "board-game-data"
            / "scraped"
            / "bgg_GameItem.csv"
        )
        .resolve()
        .as_uri(),
    )
    item_classes = (GameItem,)

    url = (
        "https://api.geekdo.com/api/historicalrankgraph"
        + "?objectid={item_id}&objecttype=thing&rankobjectid={game_type_id}"
    )
    game_types = {
        "overall": 1,
        "war": 4664,
        "children": 4665,
        "abstract": 4666,
        "customizable": 4667,
        "thematic": 5496,
        "strategy": 5497,
        "party": 5498,
        "family": 5499,
    }
    id_field = "bgg_id"

    custom_settings = {
        "DOWNLOAD_DELAY": 0.5,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 4,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 2,
        "DELAYED_RETRY_ENABLED": True,
        "DELAYED_RETRY_HTTP_CODES": (202,),
        "DELAYED_RETRY_DELAY": 5.0,
        "AUTOTHROTTLE_HTTP_CODES": (429, 503, 504),
        "ROBOTSTXT_OBEY": False,
        "ITEM_PIPELINES": {"scrapy_extensions.ValidatePipeline": None},
    }

    def get_game_type(self) -> str:
        """Get the game type from settings."""
        return (
            getattr(self, "game_type", None)
            or self.settings.get("GAME_TYPE")
            or os.getenv("GAME_TYPE")
            or "overall"
        )

    def get_game_type_id(self, game_type: Optional[str] = None) -> Optional[int]:
        """Get the object ID corresponding to the game type."""
        game_type = game_type or self.get_game_type()
        return self.game_types.get(game_type)

    def parse_csv(self, text, id_field=None):
        """Parse a CSV string for IDs."""
        id_field = id_field or self.id_field
        file = StringIO(text, newline="")
        for game in csv.DictReader(file):
            item_id = parse_int(game.get(id_field))
            if item_id:
                yield item_id, game.get("name")

    def parse(self, response):
        """
        @url TODO
        @returns items TODO TODO
        @returns requests TODO TODO
        @scrapes TODO
        """

        game_type = self.get_game_type()
        game_type_id = self.get_game_type_id(game_type)
        if not game_type_id:
            self.logger.error("Invalid game type <%s>, aborting", game_type)
            return
        self.logger.info(
            "Scraping rankings for game type <%s> (ID %d)",
            game_type,
            game_type_id,
        )

        try:
            for item_id, name in self.parse_csv(response.text):
                meta = {"name": name, "item_id": item_id}
                yield Request(
                    url=self.url.format(game_type_id=game_type_id, item_id=item_id),
                    callback=self.parse_game,
                    meta=meta,
                )

        except Exception:
            self.logger.exception(
                "Response <%s> cannot be processed as CSV",
                response.url,
            )

    def parse_game(self, response):
        """TODO."""

        result = json_from_response(response)
        data = result.get("data") or ()

        name = response.meta.get("name")
        item_id = parse_int(response.meta.get("item_id")) or parse_int(
            extract_query_param(response.url, "objectid")
        )

        if not item_id:
            self.logger.warning(
                "Unable to extract item ID from <%s>, skipping…",
                response.url,
            )
            return

        scraped_at = now()

        for date, rank in data:
            published_at = parse_date(date / 1000, tzinfo=timezone.utc)
            yield GameItem(
                name=name,
                bgg_id=item_id,
                rank=rank,
                published_at=published_at,
                scraped_at=scraped_at,
            )
