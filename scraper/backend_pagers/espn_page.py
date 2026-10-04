# backend_pagers/espn_page.py
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

import time
from .abstract import pager
from ..debug import debug

# ESPN serves every endpoint as JSON, so unlike nba_page there is no
# __NEXT_DATA__ / soup fallback to worry about and no per-host header logic.
# Requests span three hosts (site.api, site.web.api, sports.core.api), so the
# source passes base_url= for the ones that are not this pager's default.
class espn_page(pager):
    last_time = 0
    # ESPN's API is CDN backed and does not require TLS impersonation, so it
    # tolerates a tighter throttle than stats.nba.com. Pass wait_time= to the
    # constructor to tune it for a given crawl.
    DEFAULT_WAIT_TIME = 1
    DEFAULT_TIMEOUT = 20
    RETRIES = 3
    RETRY_BACKOFF = 5

    # game_info and game_data request the same event URL. A season crawl
    # interleaves the event summary with team and player lookups, so the cache
    # has to be big enough to keep the summary alive between those requests.
    DEFAULT_CACHE_SIZE = 32

    def __init__(self, cache_size=DEFAULT_CACHE_SIZE, base_url=None,
                 wait_time=DEFAULT_WAIT_TIME):
        super().__init__(cache_size, base_url)
        self.wait_time = wait_time
        # Per-instance, not a class attribute: a class-level dict would be
        # shared by every pager in the process, so an unrelated pager's
        # entries would leak into this one and never be evicted.
        self.cache = {}
        import curl_cffi.requests as requests
        self.session = requests.Session()

    def _fetch(self, url):
        return self.session.get(
            url, impersonate="chrome", timeout=self.DEFAULT_TIMEOUT
        )

    def check_cache(self, href):
        try:
            output = self.cache[href]
        except KeyError:
            output = None
            success = False
        else:
            success = True
        return success, output

    def to_cache(self, href, data):
        if len(self.cache) == self.cache_size:
            tmp = list(self.cache.items())
            tmp.reverse()
            out = tmp.pop()
            tmp.reverse()
            self.cache = dict(tmp)
        self.cache.update({href: data})

    def get(self, href, cache=True, base_url=None):
        if base_url is None:
            base_url = self.base_url
        url = base_url + href

        if cache:
            status, data = self.check_cache(href)
            if status:
                debug.debug(" Request  ", "from cache: " + href)
                return data

        current_time = time.time()
        sleep_time = self.wait_time - (current_time - self.last_time)
        if sleep_time > 0:
            time.sleep(sleep_time)

        debug.debug(" Request", time.strftime("%H:%M:%S") + " requesting " + href)
        t0 = time.time()
        # A missing or unusable response is an empty dict rather than an
        # exception, so one bad event cannot end a season-long crawl. Retries
        # are bounded; unlike the basketball-reference pager there is no
        # "wait in jail forever" loop that can hang a scrape indefinitely.
        data = {}
        status_text = "no usable response"
        for attempt in range(1, self.RETRIES + 1):
            try:
                resp = self._fetch(url)
            except Exception as e:
                debug.debug(
                    "  Error   ",
                    "Request failed (attempt %d/%d): %s" % (attempt, self.RETRIES, e),
                )
            else:
                if resp.status_code == 404:
                    status_text = "HTTP 404"
                    break
                if resp.status_code < 400:
                    try:
                        data = resp.json()
                    except Exception:
                        status_text = "undecodable JSON (HTTP %s)" % resp.status_code
                    else:
                        status_text = "HTTP %s" % resp.status_code
                    break
                if 400 <= resp.status_code < 500 and resp.status_code != 429:
                    # A WAF rejection ("Access Denied") or other client error is
                    # terminal: retrying cannot turn it into a 200, and the
                    # backoff would cost 15s per bad href over a long crawl.
                    # 429 is the exception -- it means back off and try again.
                    status_text = "HTTP %s" % resp.status_code
                    break
                debug.debug(
                    "  Error   ",
                    "HTTP %s (attempt %d/%d)"
                    % (resp.status_code, attempt, self.RETRIES),
                )
            if attempt < self.RETRIES:
                time.sleep(self.RETRY_BACKOFF * attempt)
        self.last_time = time.time()
        debug.debug(
            " Request",
            "done %s in %s (%s)" % (href, "%.1fs" % (time.time() - t0), status_text),
        )

        if cache:
            self.to_cache(href, data)

        return data
