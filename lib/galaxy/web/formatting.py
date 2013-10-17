import locale
from string import Template

DEFAULT_DATETIME_FORMAT = "$locale (UTC)"
DEFAULT_LOCALE_FORMAT = '%a %b %e %H:%M:%S %Y'


def expand_pretty_datetime_format(value):
    """

    >>> expand_pretty_datetime_format("%H:%M:%S %Z")
    '%H:%M:%S %Z'
    >>> locale_format = expand_pretty_datetime_format("$locale (UTC)")
    >>> import locale
    >>> expected_format = '%s (UTC)' % locale.nl_langinfo(locale.D_T_FMT)
    >>> locale_format == expected_format
    True
    """
    if not value:
        value = DEFAULT_DATETIME_FORMAT

    locale_format = None
    try:
        locale_format = locale.nl_langinfo(locale.D_T_FMT)
    except AttributeError:  # nl_langinfo not available
        pass
    if not locale_format:
        locale_format = DEFAULT_LOCALE_FORMAT

    return Template(value).safe_substitute(locale=locale_format)
