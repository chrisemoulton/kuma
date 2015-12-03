from collections import OrderedDict
import mock
from nose.tools import ok_, eq_

from django.utils import translation
from rest_framework import serializers
from rest_framework.test import APIRequestFactory

from kuma.wiki.search import WikiDocumentType

from . import ElasticTestCase
from ..fields import SearchQueryField, SiteURLField
from ..models import Filter, FilterGroup
from ..serializers import (DocumentSerializer, FilterSerializer,
                           FilterWithGroupSerializer)


class SerializerTests(ElasticTestCase):
    fixtures = ElasticTestCase.fixtures + ['wiki/documents.json',
                                           'search/filters.json']

    def test_filter_serializer(self):
        group = FilterGroup.objects.get(name='Group')
        filter_ = Filter.objects.create(name='Serializer', slug='serializer',
                                        group=group)
        filter_.tags.add('tag')
        filter_serializer = FilterWithGroupSerializer(filter_)
        eq_(filter_serializer.data, {
            'name': 'Serializer',
            'slug': 'serializer',
            'tags': ['tag'],
            'operator': 'OR',
            'group': OrderedDict({
                'order': 1,
                'name': 'Group',
                'slug': 'group',
            }),
            'shortcut': None,
        })

    @mock.patch('kuma.search.serializers.ugettext')
    def test_filter_serializer_with_translations(self, _mock):
        _mock.return_value = u'Juegos'
        translation.activate('es')
        filter_ = Filter(name='Games', slug='games')
        serializer = FilterSerializer(filter_)
        eq_(serializer.data, {
            'name': u'Juegos',
            'slug': u'games',
            'shortcut': None})

    def test_document_serializer(self):
        search = WikiDocumentType.search()
        result = search.execute()
        doc_serializer = DocumentSerializer(result, many=True)
        list_data = doc_serializer.data
        eq_(len(list_data), 7)
        ok_(isinstance(list_data, list))
        ok_(1 in [data['id'] for data in list_data])

        doc_serializer = DocumentSerializer(result[0], many=False)
        dict_data = doc_serializer.data
        ok_(isinstance(dict_data, dict))
        eq_(dict_data['id'], result[0].id)

    def test_excerpt(self):
        search = WikiDocumentType.search()
        search = search.query('match', summary='CSS')
        search = search.highlight(*WikiDocumentType.excerpt_fields)
        result = search.execute()
        serializer = DocumentSerializer(result, many=True)
        eq_(serializer.data[0]['excerpt'], u'A <em>CSS</em> article')


class SearchQueryFieldSerializer(serializers.Serializer):
    q = SearchQueryField()


class FieldTests(ElasticTestCase):

    def test_SearchQueryField(self):
        request = APIRequestFactory().get('/?q=test')
        # APIRequestFactory doesn't actually return APIRequest objects
        # but standard HttpRequest objects due to the way it initializes
        # the request when APIViews are called
        request.query_params = request.GET
        serializer = SearchQueryFieldSerializer(
            data={},
            context={'request': request},
        )
        serializer.is_valid()
        eq_(serializer.data, {'q': 'test'})

    def test_SiteURLField(self):
        class FakeValue(object):
            slug = 'Firefox'
            locale = 'de'

        field = SiteURLField('wiki.document', args=['slug'])
        value = field.to_representation(FakeValue())
        ok_('/de/docs/Firefox' in value)
