from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 50


# Backwards-compatible alias for callers using the older name.
DefaultPagination = StandardPagination
