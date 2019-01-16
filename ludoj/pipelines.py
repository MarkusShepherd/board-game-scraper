# -*- coding: utf-8 -*-

''' Scrapy item pipelines '''

import logging
import math

import jmespath

from scrapy import Request
from scrapy.exceptions import DropItem, NotConfigured
from scrapy.utils.defer import defer_result
from scrapy.utils.misc import arg_to_iter
from scrapy.utils.python import flatten
from twisted.internet.defer import DeferredList

from .utils import clear_list, first, parse_json

LOGGER = logging.getLogger(__name__)


class ValidatePipeline:
    ''' validate items '''

    # pylint: disable=no-self-use,unused-argument
    def process_item(self, item, spider):
        ''' verify if all required fields are present '''

        if all(item.get(field) for field in item.fields if item.fields[field].get('required')):
            return item

        raise DropItem('Missing required field in {}'.format(item))


class DataTypePipeline:
    ''' convert fields to their required data type '''

    # pylint: disable=no-self-use,unused-argument
    def process_item(self, item, spider):
        ''' convert to data type '''

        for field in item.fields:
            dtype = item.fields[field].get('dtype')
            default = item.fields[field].get('default', NotImplemented)

            if item.get(field) is None and default is not NotImplemented:
                item[field] = default() if callable(default) else default

            if not dtype or item.get(field) is None or isinstance(item[field], dtype):
                continue

            try:
                item[field] = dtype(item[field])
            except Exception as exc:
                if default is NotImplemented:
                    raise DropItem(
                        'Could not convert field "{}" to datatype "{}" in item "{}"'
                        .format(field, dtype, item)) from exc

                item[field] = default() if callable(default) else default

        return item


class ResolveLabelPipeline:
    ''' resolve labels '''

    @classmethod
    def from_crawler(cls, crawler):
        ''' init from crawler '''

        url = crawler.settings.get('RESOLVE_LABEL_URL')
        fields = crawler.settings.getlist('RESOLVE_LABEL_FIELDS')

        if not url or not fields:
            raise NotConfigured

        lang_priorities = crawler.settings.getlist('RESOLVE_LABEL_LANGUAGE_PRIORITIES')

        return cls(url=url, fields=fields, lang_priorities=lang_priorities)

    def __init__(self, url, fields, lang_priorities=None):
        self.url = url
        self.fields = fields
        self.lang_priorities = {
            lang: prio for prio, lang in enumerate(arg_to_iter(lang_priorities))
        }
        self.labels = {}
        self.logger = LOGGER

    def _extract_labels(self, response, value):
        self.logger.info('_extract_labels(%r, %r)', response, value)
        json_obj = parse_json(response.text) if hasattr(response, 'text') else {}

        labels = first(jmespath.search(f'entities.{value}.labels[0]', json_obj)) or {}
        labels = labels.values()
        labels = sorted(
            labels, key=lambda label: self.lang_priorities.get(label.get('language'), math.inf))
        labels = clear_list(label.get('value') for label in labels)

        self.labels[value] = labels
        self.logger.info('labels: %s', labels)

        return labels

    def _deferred_value(self, value, spider):
        labels = self.labels.get(value)
        if labels is not None:
            return defer_result(labels)

        request = Request(self.url.format(value))
        deferred = spider.crawler.engine.download(request, spider)
        deferred.addBoth(self._extract_labels, value)
        return deferred

    def _add_value(self, result, field, item):
        self.logger.info('_add_value(%r, %r, %r)', result, field, item)
        item[field] = clear_list(flatten(arg_to_iter(result)))
        return item

    def _deferred_field(self, field, item, spider):
        deferred = DeferredList(
            [self._deferred_value(value, spider) for value in arg_to_iter(item.get(field))],
            consumeErrors=True)
        deferred.addBoth(self._add_value, field, item)

    def process_item(self, item, spider):
        ''' resolve IDs to labels in specified fields '''

        deferred = DeferredList(
            [self._deferred_field(field, item, spider) for field in self.fields],
            consumeErrors=True)
        deferred.addBoth(lambda _: item)
        return deferred
