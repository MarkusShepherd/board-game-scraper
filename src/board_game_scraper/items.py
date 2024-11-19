from __future__ import annotations

from typing import TYPE_CHECKING

from attr import define

if TYPE_CHECKING:
    from datetime import datetime


@define(kw_only=True)
class GameItem:
    name: str
    alt_name: list[str] | None = None
    year: int | None = None
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

    min_players: int | None = None
    max_players: int | None = None
    min_players_rec: int | None = None
    max_players_rec: int | None = None
    min_players_best: int | None = None
    max_players_best: int | None = None
    min_age: int | None = None
    max_age: int | None = None
    min_age_rec: float | None = None
    max_age_rec: float | None = None
    min_time: int | None = None
    max_time: int | None = None

    category: list[str] | None = None
    mechanic: list[str] | None = None
    cooperative: bool | None = None
    compilation: bool | None = None
    compilation_of: list[int] | None = None
    family: list[str] | None = None
    expansion: list[str] | None = None
    implementation: list[int] | None = None
    integration: list[int] | None = None

    rank: int | None = None
    add_rank: list[dict[str, int]] | None = None
    num_votes: int | None = None
    avg_rating: float | None = None
    stddev_rating: float | None = None
    bayes_rating: float | None = None
    complexity: float | None = None
    language_dependency: float | None = None

    bgg_id: int | None = None
    freebase_id: str | None = None
    wikidata_id: str | None = None
    wikipedia_id: str | None = None
    dbpedia_id: str | None = None
    luding_id: int | None = None
    spielen_id: str | None = None

    published_at: datetime | None = None
    updated_at: datetime | None = None
    scraped_at: datetime  # TODO: Default to datetime.now()
