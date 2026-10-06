# debug.py
#
# Copyright (C) 2025 Carson Buttars
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""Logging for the scraper.

Output goes to stdout through a single StreamHandler on the library's own
"scraper" logger. The handler flushes after every record, which is what the
old bare print() calls failed to do: redirected to a file stdout is
block-buffered, so an entire season's log sat in the buffer and only appeared
when the process exited.
"""

import logging
import sys

LOG_FORMAT = "%(asctime)s [%(levelname)-7s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%H:%M:%S"

# Exceptions that mean "the source does not publish this field", as opposed to
# "this code is broken". The first is an assumption worth an INFO line; the
# second must never be allowed to look like a routine fallback.
DATA_ABSENCE_ERRORS = (KeyError, IndexError, AttributeError, TypeError, ValueError)

# Which (location, field, value) triples have already been announced at INFO.
# A crawl is single threaded, so a plain set is enough.
_assumed = set()

_configured = False


def configure(level = None):
    """Attach the library's stdout handler, and optionally set its level.

    Idempotent. Called without a level it only makes sure the handler exists,
    which is what make_engine does so that a bare `import scraper` still logs;
    the scripts pass the level their -q/-v flags select. The level is left
    alone by a level-less call, so configure(-q) before make_engine keeps -q.

    The first call also clears the reported-assumption set, so each fresh
    configure starts a fresh run.
    """
    global _configured

    logger = logging.getLogger("scraper")
    if _configured:
        if level is not None:
            logger.setLevel(level)
        return logger

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO if level is None else level)
    _configured = True
    _assumed.clear()

    # StreamHandler already flushes per record; this also covers any stray
    # direct print(). stdout is not always a tty and not always reconfigurable.
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        try:
            reconfigure(line_buffering = True)
        except (ValueError, OSError):
            pass

    return logger


def get_logger(name):
    """Return a logger inside the library's namespace.

    Accepts a bare label ("player_info") or a fully qualified module name,
    which is the usual logging.getLogger(__name__) result.
    """
    if not name.startswith("scraper."):
        name = "scraper." + name
    return logging.getLogger(name)


def assume(location, field, value, reason, context = None, log = None):
    """Record that `value` was substituted because the source published none.

    The per-row detail goes to DEBUG, so -v still shows which player or game
    was affected. The first sighting of each (location, field, value) triple
    goes to INFO, so the default-level log states once what was assumed
    instead of repeating it for every row: a whole NBA season's worth of
    Shoots="R" defaults is one line, not 347.
    """
    logger = get_logger(location) if log is None else log

    if context is None:
        logger.debug("assuming %s.%s=%r (%s)", location, field, value, reason)
    else:
        logger.debug("assuming %s.%s=%r for %s (%s)",
                     location, field, value, context, reason)

    key = (location, field, repr(value))
    if key in _assumed:
        return
    _assumed.add(key)
    logger.info("assuming %s.%s=%r (%s)", location, field, value, reason)


class debug:
    """Mixin giving the *_info classes error handling.

    Kept as a mixin because the classes in abstract.py inherit it, and 31
    error_wrap sites depend on the contract this provides: log what could not
    be filled and return a usable default rather than raising. The old static
    debug() method is gone; each module now does
    `log = logging.getLogger(__name__)`.
    """

    def _context_href(self, soup):
        """Best page context for a failed field.

        The object's own href identifies the row it was being filled for, so
        it beats the canonical-link lookup below, which is
        basketball-reference-specific and degrades silently for the other
        sources.
        """
        href = getattr(self, 'href', None)
        if href:
            return href

        try:
            url = soup.find('link', {'rel': 'canonical'}).attrs['href']
        except Exception:
            return 'This comes from the most recent page that was requested.'
        return url.replace('https://www.basketball-reference.com', '')

    def debug_error(self, soup, location, field, return_type, info = '',
                    default = None, error = None, log = None):
        """Resolve the default for a field the source would not fill, and say so.

        Returns the default rather than raising: an absent row is recoverable,
        a plausible-looking wrong one is not, and every error_wrap site counts
        on that.
        """
        if not (isinstance(return_type, type) or return_type == None):
            raise TypeError

        if default != None:
            output = default
        elif return_type == int:
            output = 0
        elif return_type == str:
            output = ''
        elif return_type == bool:
            output = False
        elif return_type == list:
            output = []
        elif return_type == None:
            output = return_type
        else:
            output = 0

        logger = get_logger(location) if log is None else log
        href = self._context_href(soup)

        if error is None:
            reason = 'field is unavailable'
        else:
            reason = '%s: %s' % (type(error).__name__, error)
        if info != '':
            reason = '%s (%s)' % (reason, info)

        assume(location, field, output, reason, context = href, log = logger)

        # A data-shaped exception is the expected outcome of asking a source
        # for something it does not publish. Anything else means the code broke
        # and must not be mistaken for a routine fallback, so it is reported
        # loudly on top of the assumption.
        if error is not None and not isinstance(error, DATA_ABSENCE_ERRORS):
            logger.error("unexpected %s filling %s.%s for %s: %s",
                         type(error).__name__, location, field, href, error)

        return output

    def error_wrap(location = '', field = '', return_type = '', info = '',
                   default = None):
        def decorator(function):
            def wrapper(self, *args, **kwargs):
                try:
                    return function(self, *args, **kwargs)
                # Exception, not bare except: a KeyboardInterrupt should reach
                # the user instead of silently turning into a default.
                except Exception as error:
                    return self.debug_error(self.soup, location, field,
                                            return_type, info, default, error,
                                            get_logger(function.__module__))
            return wrapper
        return decorator
