import time
import requests
from bs4 import BeautifulSoup
from debug import debug

class page:

    def __init__(self, cache_size):
        self.cache_size = cache_size

    base_url = 'https://basketball-reference.com'
    last_time = 0
    wait_time = 4
    cache = {}

    user_agents = ["Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Safari/605.1.1",
                   "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.3",
                   "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.3",
                   "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Mobile/15E148 Safari/604.",
                   "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.1",
                   "Mozilla/5.0 (Linux; Android 9; JAT-L41) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.125 Mobile Safari/537.3",
                   "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.",
                   "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/122.0.6261.89 Mobile/15E148 Safari/604.",
                   "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.",
                   "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.3",
                   "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.3",
                   "Mozilla/5.0 (iPhone; CPU iPhone OS 16_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.2 Mobile/15E148 Safari/604.",
                   "Mozilla/5.0 (X11; CrOS x86_64 14541.0.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.3",
                   "Mozilla/5.0 (Linux; Android 13; 22101320G Build/TKQ1.221114.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/108.0.5359.128 Mobile Safari/537.3",
                   "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.",
                   "Mozilla/5.0 (Linux; U; Android 14; sk-sk; Redmi Note 12 Build/UKQ1.230917.001) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/112.0.5615.136 Mobile Safari/537.36 XiaoMi/MiuiBrowser/14.6.0-g",
                   "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.",
                   "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.",
                   "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.3",
                   "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/24.0 Chrome/117.0.0.0 Mobile Safari/537.3"]
    agent_index = 0

    def redo_for_scorebox(self, href, soup):
        if 'boxscores' in href:
            x = soup.find('div', {'class': 'scorebox'})
            if x is None:
                return True
            else:
                return False
        else:
            return False

    def to_cache(self, href, soup):
        if len(self.cache) == self.cache_size:
            tmp = list(self.cache.items())
            tmp.reverse()
            out = tmp.pop()
            tmp.reverse()
            self.cache = dict(tmp)

        self.cache.update({href: soup})

    def check_cache(self, href):
        try:
            output = self.cache[href]
        except:
            output = 'Not found'
            success = False
        else:
            success = True

        return success, output

    def needs_refresh(self, soup):
        tag = soup.find('meta', {'http-equiv': 'refresh'})
        if tag:
            return True
        else:
            return False

    def get(self, href, cache = True):
        url = self.base_url + href

        cache_status = 'Not found'

        if cache:
            status, soup = self.check_cache(href)
        
        if cache and status:
            debug.debug(' Request  ', 'from cache: ' + href)
            return soup

        headers = {'User-Agent': self.user_agents[self.agent_index],
                   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                   'Accept-Language': 'en-US,en;q=0.5',
                   'Accept-Encoding': 'gzip, deflate, br',
                   'Connection': 'keep-alive',
                   'Cookie': 'sr_note_box_countdown=47; srcssfull=yes; is_live=true; usprivacy=1NYN; sr_n=1%7CTue%2C%2026%20Mar%202024%2001%3A44%3A59%20GMT; __cf_bm=9.msJrpwm.xXzhQ1.FXyR_WXTKfxOEj3CehtphfekQo-1711435471-1.0.1.1-Af53Ht0BQKLpw7Ez_.W2SwU6g4JteYQobP5O9iqig3bMCz7Ss3C7QJx4gVMaEB_MnoioonwsKWY3QWTC2SdkQQ',
                   'Upgrade-Insecure-Requests': 1,
                   'Sec-Fetch-Dest': 'document',
                   'Sec-Fetch-Mode': 'navigate',
                   'Sec-Fetch-Site': 'cross-site',
                   'DNT': 1,
                   'Sec-GPC': 1}
        self.agent_index += 1

        if self.agent_index == len(self.user_agents):
            self.agent_index = 0

        current_time = time.time()
        sleep_time = self.wait_time - (current_time - self.last_time)

        if sleep_time > 0:
            time.sleep(sleep_time)

        page = requests.get(url)
        page.encoding = page.apparent_encoding
        soup = BeautifulSoup(page.text, features="lxml")
        self.last_time = time.time()
        time_string = time.strftime('%H:%M:%S', time.localtime(self.last_time))
        debug.debug(' Request  ', time_string + '  requesting: ' + href)

        # Sometimes boxscore pages don't get requested correctly
        if self.redo_for_scorebox(href, soup):
            debug.debug(' Request  ', 'Found an error on boxscore page; new request:\t' + href)
            return self.get(new_href, cache)

        # Sometimes we get a refresh page
        if self.needs_refresh(soup):
            tag = soup.find('meta', {'http-equiv': 'refresh'})
            new_href = tag.attrs['content'].replace('1;URL=', '')
            debug.debug(' Request  ', "Got a refresh response; new request:\t" + new_href)
            return self.get(new_href, cache)

        # Just try again before we make a decision
        if not page.ok:
            time.sleep(20)
            page = requests.get(url)

        # We probably are blocked
        if page.status_code >= 400:
            debug.debug('  Error   ',
                        'Requests: Probably too many requests, will be in jail until an hour after ' + time_string + '. Will keep trying intermitently.')
            while not page.ok:
                time.sleep(60)
                page = requests.get(url)

            soup = BeautifulSoup(page.text, features="lxml")

        if cache:
            self.to_cache(href, soup)

        return soup
