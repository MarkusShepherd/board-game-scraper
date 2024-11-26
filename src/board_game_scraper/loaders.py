from functools import partial

from itemloaders.processors import Identity, MapCompose, TakeFirst
from scrapy.loader import ItemLoader
from w3lib.html import replace_entities

from board_game_scraper.items import CollectionItem, GameItem, UserItem
from board_game_scraper.utils.parsers import parse_date, parse_float, parse_int
from board_game_scraper.utils.strings import normalize_space

normalize_space_with_newline = partial(normalize_space, preserve_newline=True)


class GameLoader(ItemLoader):
    default_item_class = GameItem
    # default_input_processor = MapCompose(...)
    default_output_processor = TakeFirst()

    alt_name_out = Identity()
    year_in = MapCompose(parse_int)
    game_type_out = Identity()
    description_in = MapCompose(normalize_space_with_newline)

    designer_out = Identity()
    artist_out = Identity()
    publisher_out = Identity()

    official_url_out = Identity()
    image_url_out = Identity()
    video_url_out = Identity()
    rules_url_out = Identity()
    review_url_out = Identity()
    external_link_out = Identity()

    min_players_in = MapCompose(parse_int)
    max_players_in = MapCompose(parse_int)
    min_players_rec_in = MapCompose(parse_int)
    max_players_rec_in = MapCompose(parse_int)
    min_players_best_in = MapCompose(parse_int)
    max_players_best_in = MapCompose(parse_int)
    min_age_in = MapCompose(parse_int)
    max_age_in = MapCompose(parse_int)
    min_age_rec_in = MapCompose(parse_float)
    max_age_rec_in = MapCompose(parse_float)
    min_time_in = MapCompose(parse_int)
    max_time_in = MapCompose(parse_int)

    category_out = Identity()
    mechanic_out = Identity()
    compilation_of_in = MapCompose(parse_int)
    compilation_of_out = Identity()
    family_out = Identity()
    expansion_out = Identity()
    implementation_in = MapCompose(parse_int)
    implementation_out = Identity()
    integration_in = MapCompose(parse_int)
    integration_out = Identity()

    rank_in = MapCompose(parse_int)
    add_rank_out = Identity()
    num_votes_in = MapCompose(parse_int)
    avg_rating_in = MapCompose(parse_float)
    stddev_rating_in = MapCompose(parse_float)
    bayes_rating_in = MapCompose(parse_float)

    complexity_in = MapCompose(parse_float)
    language_dependency_in = MapCompose(parse_float)

    bgg_id_in = MapCompose(parse_int)
    luding_id_in = MapCompose(parse_int)

    published_at_in = MapCompose(parse_date)
    updated_at_in = MapCompose(parse_date)
    scraped_at_in = MapCompose(parse_date)


class BggGameLoader(GameLoader):
    description_in = MapCompose(replace_entities, normalize_space_with_newline)


class UserLoader(ItemLoader):
    default_item_class = UserItem
    # default_input_processor = MapCompose(...)
    default_output_processor = TakeFirst()

    item_id_in = MapCompose(parse_int)

    registered_in = MapCompose(parse_int)
    last_login_in = MapCompose(parse_date)

    external_link_out = Identity()
    image_url_out = Identity()

    published_at_in = MapCompose(parse_date)
    updated_at_in = MapCompose(parse_date)
    scraped_at_in = MapCompose(parse_date)


class CollectionLoader(ItemLoader):
    default_item_class = CollectionItem
    # default_input_processor = MapCompose(...)
    default_output_processor = TakeFirst()

    bgg_id_in = MapCompose(parse_int)

    bgg_user_rating_in = MapCompose(parse_float)
    bgg_user_wishlist_in = MapCompose(parse_int)
    bgg_user_play_count_in = MapCompose(parse_int)

    comment_in = MapCompose(normalize_space_with_newline)

    published_at_in = MapCompose(parse_date)
    updated_at_in = MapCompose(parse_date)
    scraped_at_in = MapCompose(parse_date)
