from collections import OrderedDict
from django.conf import settings
from django.core.paginator import InvalidPage
from django.utils import six
from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .paginator import SearchPaginator


class SearchPagination(PageNumberPagination):
    page_size = 10
    max_page_size = 100
    page_size_query_param = 'per_page'
    template = None

    def paginate_queryset(self, queryset, request, view=None):
        """
        Paginate a queryset if required, either returning a
        page object, or `None` if pagination is not configured for this view.
        """
        page_size = self.get_page_size(request)
        if not page_size:
            return None

        # REDFLAG: This is the line we had to modify in this method :(
        # this method can be simplified when django-rest-framework 3.3.2 is out
        # https://github.com/tomchristie/django-rest-framework/pull/3631
        paginator = SearchPaginator(queryset, page_size)
        page_number = request.query_params.get(self.page_query_param, 1)
        if page_number in self.last_page_strings:
            page_number = paginator.num_pages

        try:
            self.page = paginator.page(page_number)
        except InvalidPage as exc:
            msg = self.invalid_page_message.format(
                page_number=page_number, message=six.text_type(exc)
            )
            raise NotFound(msg)

        if paginator.num_pages > 1 and self.template is not None:
            # The browsable API should display pagination controls.
            self.display_page_controls = True

        self.request = request

        # We store the view here to be able to fetch the filters from it
        self.view = view
        return list(self.page)

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('query', self.request.query_params.get('q')),
            ('locale', getattr(
                self.request,
                'LANGUAGE_CODE',
                settings.WIKI_DEFAULT_LANGUAGE
            )),
            ('page', self.page.number),
            ('pages', self.page.paginator.num_pages),
            ('start', self.page.start_index()),
            ('end', self.page.end_index()),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('count', self.page.paginator.count),
            ('filters', self.view.get_filters(self.page.aggregations)),
            ('documents', data),
        ]))
