from functools import partial

from itemloaders.processors import Identity, MapCompose, TakeFirst
from scrapy.loader import ItemLoader
from w3lib.html import replace_entities

from board_game_scraper.items import CollectionItem, GameItem
from board_game_scraper.utils.parsers import parse_float, parse_int
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

    bgg_id_in = MapCompose(parse_int)


class BggGameLoader(GameLoader):
    description_in = MapCompose(replace_entities, normalize_space_with_newline)


class CollectionLoader(ItemLoader):
    default_item_class = CollectionItem
    # default_input_processor = MapCompose(...)
    default_output_processor = TakeFirst()

    bgg_id_in = MapCompose(parse_int)

    bgg_user_rating_in = MapCompose(parse_float)
    bgg_user_wishlist_in = MapCompose(parse_int)
    bgg_user_play_count_in = MapCompose(parse_int)

    comment_in = MapCompose(normalize_space_with_newline)
