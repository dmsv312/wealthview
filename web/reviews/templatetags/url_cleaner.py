# Стандартный импорт библиотеки шаблонов
from django import template

# Это чтобы register.filter работал
register = template.Library()


# Расскажем django о нашем крутом фильтре
@register.filter
def clean_order_by(url):
    args = [
        "-date",
        "-rating",
        "-popularity",
        "date",
        "rating",
        "popularity",
    ]

    for arg in args:
        if url.__contains__(arg):
            url = url.replace("&order_by=%s" % arg, "")

    return url
