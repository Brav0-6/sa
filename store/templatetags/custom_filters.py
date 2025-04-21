from django import template

register = template.Library()

@register.filter(name='sub')
def sub(value, arg):
    """Subtract the arg from the value."""
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        try:
            return float(value) - float(arg)
        except (ValueError, TypeError):
            return ''

@register.filter(name='add')
def add(value, arg):
    """Add the arg to the value."""
    try:
        return int(value) + int(arg)
    except (ValueError, TypeError):
        try:
            return float(value) + float(arg)
        except (ValueError, TypeError):
            return ''

@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Template filter to retrieve an item from a dictionary by its key
    Usage: {{ mydict|get_item:key_variable }}
    """
    try:
        return dictionary.get(int(key), 0)
    except (ValueError, AttributeError, TypeError):
        return dictionary.get(key, 0)

@register.filter(name='mul')
def mul(value, arg):
    """Multiply the value by the arg."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter(name='div')
def div(value, arg):
    """Divide the value by the arg."""
    try:
        if float(arg) == 0:
            return 0
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter(name='map')
def map_filter(iterable, attribute):
    """
    Maps an attribute of objects in an iterable to a list
    Usage: {{ users|map:'username' }} will return a list of all usernames
    """
    if iterable is None:
        return []
    
    result = []
    for obj in iterable:
        if isinstance(obj, dict):
            result.append(obj.get(attribute))
        else:
            result.append(getattr(obj, attribute, None))
    
    return result 