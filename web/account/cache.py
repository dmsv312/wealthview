from django.core.cache import cache


class PortfolioCacheBase:
    """
        Старый кэш, который использовался с редисом
    """
    def __init__(self, portfolio):
        self.portfolio = portfolio
        self.portfolio_id = str(self.portfolio.id)

    def get_cache_name(self):
        return f'portfolio{self.portfolio_id}'

    def set(self, **kwargs):
        old_value = cache.get(self.get_cache_name()) or {}
        old_value.update(kwargs)
        cache.set(self.get_cache_name(), old_value)

    def get(self, name=None):
        portfolio_cache = cache.get(self.get_cache_name())

        if portfolio_cache:
            if name:
                return portfolio_cache.get(name)
            else:
                return portfolio_cache

    def clear(self):
        cache.delete(self.get_cache_name())


class PortfolioCache(PortfolioCacheBase):
    """
        Новый кэш, который хранит данные по портфелю в ЛК
    """

    def set(self, **kwargs):
        if not self.portfolio.data:
            self.portfolio.data = kwargs
        else:
            self.portfolio.data.update(kwargs)
        self.portfolio.save()

    def get(self, name=None):
        portfolio_data = self.portfolio.data

        if portfolio_data:
            if name:
                return portfolio_data.get(name)
            else:
                return portfolio_data

    def clear(self):
        self.portfolio.data = None
        self.portfolio.save()
