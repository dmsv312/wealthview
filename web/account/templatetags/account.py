from django import template

register = template.Library()


@register.filter
def filter_operation_types(operations, asset_type):
    if asset_type in ["cash"]:
        return operations.exclude(slug__in=["Dividend"])
    else:
        return operations.filter(slug__in=["Buy", "Sell", "Dividend"])


@register.filter
def filter_open_positions(open_positions, asset_type):
    return list(filter(lambda open_position: open_position["asset"]["type"] == asset_type, open_positions))


@register.simple_tag
def portfolio_number(portfolios, portfolio):
    return list(portfolios.values_list('pk', flat=True)).index(portfolio.pk) + 1


@register.simple_tag
def portfolio_name(portfolios, portfolio):
    return portfolio.name


@register.filter
def show_ticker(value, ticker):
    if value:
        return f"{value}{ticker}"
    return ""
