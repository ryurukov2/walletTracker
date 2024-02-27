from django import template
import datetime
register = template.Library()

@register.filter(name="toDate")
def toDate(value):
    try:
        # Convert the timestamp (assumed to be in seconds) to a datetime object
        timestamp = int(value)
        converted_date = datetime.datetime.fromtimestamp(timestamp)
        return converted_date.strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        return value