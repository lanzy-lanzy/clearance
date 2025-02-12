from django import template

register = template.Library()

@register.filter(name='subtract')
def subtract(value, arg):
    """Subtracts the arg from the value"""
    try:
        return value - arg
    except (ValueError, TypeError):
        return value

@register.filter(name='has_attr')
def has_attr(obj, attr_name):
    """Checks if an object has the specified attribute"""
    return hasattr(obj, attr_name)
