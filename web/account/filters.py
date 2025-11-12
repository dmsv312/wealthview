import django_filters


class PortfolioFilter(django_filters.FilterSet):
    portfolio_id = django_filters.CharFilter(lookup_expr='iexact', field_name="id")


