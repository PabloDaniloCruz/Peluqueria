from django import template

register = template.Library()

@register.filter
def dict_get(dictionary, key):
    return dictionary.get(key)


@register.filter
def wa_phone(value):
    """Limpia un teléfono para usarlo en URL de WhatsApp: solo dígitos, sin prefijos raros."""
    import re
    return re.sub(r'\D', '', value)
