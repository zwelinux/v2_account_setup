# accounts/pagination.py
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
import math

class ProductPagination(PageNumberPagination):
    page_size = 20  # default
    page_size_query_param = 'limit'

    def get_paginated_response(self, data):
        total_products = self.page.paginator.count
        total_pages = math.ceil(total_products / self.get_page_size(self.request))
        return Response({
            "current_page": self.page.number,
            "total_pages": total_pages,
            "found_products": total_products,
            "limit": self.get_page_size(self.request),
            "has_next_page": self.page.has_next(),
            "products": data
        })
