"""
カスタムページネーション
"""
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from collections import OrderedDict


class StandardResultsSetPagination(PageNumberPagination):
    """
    標準的なページネーション設定
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('page_size', self.page_size),
            ('total_pages', self.page.paginator.num_pages),
            ('current_page', self.page.number),
            ('results', data)
        ]))


class LargeResultsSetPagination(PageNumberPagination):
    """
    大量データ用ページネーション
    """
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 500

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('page_size', self.page_size),
            ('total_pages', self.page.paginator.num_pages),
            ('current_page', self.page.number),
            ('results', data)
        ]))


class SmallResultsSetPagination(PageNumberPagination):
    """
    小規模データ用ページネーション
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('page_size', self.page_size),
            ('total_pages', self.page.paginator.num_pages),
            ('current_page', self.page.number),
            ('results', data)
        ]))


class RacePagination(StandardResultsSetPagination):
    """
    レース一覧用ページネーション
    """
    page_size = 25
    max_page_size = 100


class HorsePagination(StandardResultsSetPagination):
    """
    馬一覧用ページネーション
    """
    page_size = 30
    max_page_size = 200


class PredictionPagination(StandardResultsSetPagination):
    """
    予測結果用ページネーション
    """
    page_size = 15
    max_page_size = 50


class AnalyticsPagination(LargeResultsSetPagination):
    """
    分析データ用ページネーション
    """
    page_size = 100
    max_page_size = 1000
