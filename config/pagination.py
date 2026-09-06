from collections import OrderedDict

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class DefaultPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "per_page"
    max_page_size = 100

    def get_paginated_response_schema(self, schema):
        return {
            "type": "object",
            "required": ["data", "pagination"],
            "properties": {
                "data": schema,
                "pagination": {
                    "type": "object",
                    "required": ["page", "per_page", "total", "total_pages"],
                    "properties": {
                        "page": {"type": "integer", "minimum": 1},
                        "per_page": {"type": "integer", "minimum": 1, "maximum": 100},
                        "total": {"type": "integer", "minimum": 0},
                        "total_pages": {"type": "integer", "minimum": 1},
                    },
                },
            },
        }

    def get_paginated_response(self, data):
        return Response(
            OrderedDict(
                [
                    ("data", data),
                    (
                        "pagination",
                        OrderedDict(
                            [
                                ("page", self.page.number),
                                ("per_page", self.get_page_size(self.request)),
                                ("total", self.page.paginator.count),
                                ("total_pages", self.page.paginator.num_pages),
                            ]
                        ),
                    ),
                ]
            )
        )
