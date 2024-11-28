from typing import Any

from itemadapter import ItemAdapter
from scrapy.exporters import JsonLinesItemExporter


class SparseJsonLinesItemExporter(JsonLinesItemExporter):
    """Recursively remove falsey values from items before exporting them."""

    def remove_falsey_values(self, item: Any) -> None:
        """Recursively remove falsey values from the given item."""

        adapter = ItemAdapter(item)

        for key, value in tuple(adapter.items()):
            if not value:
                del adapter[key]

            elif ItemAdapter.is_item(value):
                self.remove_falsey_values(value)

            elif isinstance(value, (list, tuple, set, frozenset)):
                for v in value:
                    if ItemAdapter.is_item(v):
                        self.remove_falsey_values(v)

    def export_item(self, item: Any) -> None:
        """Recursively remove falsey values from the given item before exporting it."""

        self.remove_falsey_values(item)

        return super().export_item(item)
