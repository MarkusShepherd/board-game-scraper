from __future__ import annotations

from typing import TYPE_CHECKING

from attrs import converters, define, field

from board_game_scraper.utils.dates import now
from board_game_scraper.utils.parsers import parse_int

if TYPE_CHECKING:
    from datetime import datetime


@define(kw_only=True)
class GameItem:
    name: str
    alt_name: list[str] | None = None
    year: int | None = field(converter=parse_int, default=None)
    game_type: list[str] | None = None
    description: str | None = None

    designer: list[str] | None = None
    artist: list[str] | None = None
    publisher: list[str] | None = None

    url: str | None = None
    official_url: list[str] | None = None
    image_url: list[str] | None = None
    image_file: list[dict[str, str]] | None = None
    image_blurhash: list[dict[str, str]] | None = None
    video_url: list[str] | None = None
    rules_url: list[str] | None = None
    rules_file: list[dict[str, str]] | None = None
    review_url: list[str] | None = None
    external_link: list[str] | None = None
    list_price: str | None = None

    min_players: int | None = field(converter=parse_int, default=None)
    max_players: int | None = field(converter=parse_int, default=None)
    min_players_rec: int | None = field(converter=parse_int, default=None)
    max_players_rec: int | None = field(converter=parse_int, default=None)
    min_players_best: int | None = field(converter=parse_int, default=None)
    max_players_best: int | None = field(converter=parse_int, default=None)
    min_age: int | None = field(converter=parse_int, default=None)
    max_age: int | None = field(converter=parse_int, default=None)
    min_age_rec: float | None = None
    max_age_rec: float | None = None
    min_time: int | None = field(converter=parse_int, default=None)
    max_time: int | None = field(converter=parse_int, default=None)

    category: list[str] | None = None
    mechanic: list[str] | None = None
    cooperative: bool | None = None
    compilation: bool | None = None
    compilation_of: list[int] | None = None
    family: list[str] | None = None
    expansion: list[str] | None = None
    implementation: list[int] | None = None
    integration: list[int] | None = None

    rank: int | None = field(converter=parse_int, default=None)
    add_rank: list[dict[str, int]] | None = None
    num_votes: int | None = field(converter=parse_int, default=None)
    avg_rating: float | None = None
    stddev_rating: float | None = None
    bayes_rating: float | None = None
    complexity: float | None = None
    language_dependency: float | None = None

    bgg_id: int | None = field(converter=parse_int, default=None)
    freebase_id: str | None = None
    wikidata_id: str | None = None
    wikipedia_id: str | None = None
    dbpedia_id: str | None = None
    luding_id: int | None = field(converter=parse_int, default=None)
    spielen_id: str | None = None

    published_at: datetime | None = None
    updated_at: datetime | None = None
    scraped_at: datetime = field(factory=now)


@define(kw_only=True)
class UserItem:
    item_id: int | None = None
    bgg_user_name: str = field(converter=str.lower)  # type: ignore[misc]
    first_name: str | None = None
    last_name: str | None = None

    registered: int | None = field(converter=parse_int, default=None)
    last_login: datetime | None = None

    country: str | None = None
    region: str | None = None
    city: str | None = None

    external_link: list[str] | None = None
    image_url: list[str] | None = None
    image_file: list[dict[str, str]] | None = None
    image_blurhash: list[dict[str, str]] | None = None

    published_at: datetime | None = None
    updated_at: datetime | None = None
    scraped_at: datetime = field(factory=now)


@define(kw_only=True)
class CollectionItem:
    item_id: str | int
    bgg_id: int = field(converter=int)
    bgg_user_name: str = field(converter=str.lower)  # type: ignore[misc]

    bgg_user_rating: float | None = field(
        converter=float,
        default=None,
    )
    bgg_user_owned: bool | None = field(
        converter=converters.to_bool,
        default=None,
    )
    bgg_user_prev_owned: bool | None = field(
        converter=converters.to_bool,
        default=None,
    )
    bgg_user_for_trade: bool | None = field(
        converter=converters.to_bool,
        default=None,
    )
    bgg_user_want_in_trade: bool | None = field(
        converter=converters.to_bool,
        default=None,
    )
    bgg_user_want_to_play: bool | None = field(
        converter=converters.to_bool,
        default=None,
    )
    bgg_user_want_to_buy: bool | None = field(
        converter=converters.to_bool,
        default=None,
    )
    bgg_user_preordered: bool | None = field(
        converter=converters.to_bool,
        default=None,
    )
    bgg_user_wishlist: int | None = field(
        converter=parse_int,
        default=None,
    )
    bgg_user_play_count: int | None = field(
        converter=parse_int,
        default=None,
    )

    comment: str | None = None

    published_at: datetime | None = None
    updated_at: datetime | None = None
    scraped_at: datetime = field(factory=now)
