from django import template

register = template.Library()


# convert percent scale percent value from (-100-100) to (0-100)
@register.simple_tag
def convert_scale(scale):
    return (round(scale, 2) + 100) / 2


def smart_round(value):
    no_valid_values = [float("inf"), float("-inf"), "-", ""]
    if not str(value).isalpha() and value not in no_valid_values:
        value = float(value)
        if 10 < abs(value) < 100:
            value = "%.1f" % round(value, 1)
        elif abs(value) < 10:
            value = "%.2f" % round(value, 2)
        else:
            value = int(value)
        return value
    return ""


register.filter('smart_round', smart_round)
