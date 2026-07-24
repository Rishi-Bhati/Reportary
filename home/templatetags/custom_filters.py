from django import template

register = template.Library()

@register.filter(name='is_list')
def is_list(value):
    return isinstance(value, list)

@register.filter(name='get_item')
def get_item(dictionary, key):
    if not isinstance(dictionary, dict):
        return None
    return dictionary.get(str(key))
