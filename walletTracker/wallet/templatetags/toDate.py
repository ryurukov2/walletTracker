from django import template
import datetime
register = template.Library()


@register.filter(name="toDate")
def toDate(value):
    try:
        # Convert the timestamp (assumed to be in seconds) to a datetime object
        timestamp = int(value)
        converted_date = datetime.datetime.fromtimestamp(timestamp)
        # minuses in strftime rely on glibc so it only works on Linux. Will be hosted on a linux box so I don't think it's an issue
        return converted_date.strftime('%-m/%-d/%Y, %-H:%-M:%S%p')
    except ValueError:
        return value
