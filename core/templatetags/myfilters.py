from django import template

register = template.Library()

@register.filter(name='hasattr')
def hasattr_filter(obj, attr):
    return hasattr(obj, attr)
