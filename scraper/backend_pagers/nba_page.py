# nba_page.py
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

import json
import time
from bs4 import BeautifulSoup
from .abstract import pager
from ..debug import debug


def _is_json_url(url):
    return "stats.nba.com" in url or "cdn.nba.com" in url


class nba_page(pager):
    last_time = 0
    DEFAULT_WAIT_TIME = 2
    DEFAULT_TIMEOUT = 20
    RETRIES = 3
    RETRY_BACKOFF = 5
    cache = {}

    def __init__(self, cache_size, base_url, wait_time=DEFAULT_WAIT_TIME):
        super().__init__(cache_size, base_url)
        self.wait_time = wait_time
        import curl_cffi.requests as requests
        self.session = requests.Session()

    def _fetch(self, url):
        headers = {}
        if _is_json_url(url):
            headers = {
                "Referer": "https://www.nba.com/stats/",
                "Origin": "https://www.nba.com",
            }
        resp = self.session.get(url, headers=headers, impersonate="chrome",
                                timeout=self.DEFAULT_TIMEOUT)
        return resp

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

    def _extract_next_data(self, soup):
        script = soup.find("script", {"id": "__NEXT_DATA__"})
        if script and script.string:
            return json.loads(script.string)
        return {}

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

        debug.debug(' Request', time.strftime('%H:%M:%S') + ' requesting ' + href)
        t0 = time.time()
        resp = None
        for attempt in range(1, self.RETRIES + 1):
            try:
                resp = self._fetch(url)
                break
            except Exception as e:
                debug.debug(
                    "  Error   ",
                    "Request failed (attempt %d/%d): %s" % (attempt, self.RETRIES, e),
                )
                if attempt < self.RETRIES:
                    time.sleep(self.RETRY_BACKOFF * attempt)
        self.last_time = time.time()
        done = "%.1fs" % (time.time() - t0)
        if resp is None:
            data = {}
            debug.debug(' Request', 'done %s in %s (HTTP no response)' % (href, done))
        elif resp.status_code == 404:
            data = {}
            debug.debug(' Request', 'done %s in %s (HTTP 404)' % (href, done))
        elif resp.status_code >= 400:
            debug.debug(
                "  Error   ",
                "Requests: Probably too many requests, will keep trying intermittently.",
            )
            while not resp.ok:
                time.sleep(60)
                resp = self._fetch(url)

            soup = BeautifulSoup(resp.text, features="lxml")
            data = self._extract_next_data(soup)
            debug.debug(' Request', 'done %s in %s (HTTP %s)' % (href, done, resp.status_code))
        else:
            is_json = _is_json_url(url)
            if is_json:
                try:
                    data = resp.json()
                except Exception:
                    soup = BeautifulSoup(resp.text, features="lxml")
                    data = self._extract_next_data(soup)
            else:
                soup = BeautifulSoup(resp.text, features="lxml")
                data = self._extract_next_data(soup)
            debug.debug(' Request', 'done %s in %s (HTTP %s)' % (href, done, resp.status_code))

        if cache:
            self.to_cache(href, data)

        return data