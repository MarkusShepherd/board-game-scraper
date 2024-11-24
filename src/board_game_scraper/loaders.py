from itemloaders.processors import Identity, MapCompose, TakeFirst
from scrapy.loader import ItemLoader

from board_game_scraper.items import CollectionItem, GameItem
from board_game_scraper.utils.parsers import parse_float, parse_int
from board_game_scraper.utils.strings import normalize_space


class GameLoader(ItemLoader):
    default_item_class = GameItem
    # default_input_processor = MapCompose(...)
    default_output_processor = TakeFirst()

    alt_name_out = Identity()
    year_in = MapCompose(parse_int)
    game_type_out = Identity()
    description_in = MapCompose(normalize_space)

    bgg_id_in = MapCompose(parse_int)


class CollectionLoader(ItemLoader):
    default_item_class = CollectionItem
    # default_input_processor = MapCompose(...)
    default_output_processor = TakeFirst()

    bgg_id_in = MapCompose(parse_int)

    bgg_user_rating_in = MapCompose(parse_float)
    bgg_user_wishlist_in = MapCompose(parse_int)
    bgg_user_play_count_in = MapCompose(parse_int)

    comment_in = MapCompose(normalize_space)
