import re
from bs4 import BeautifulSoup, Comment

from . import abstract
from ..debug import debug

class referee_info(abstract.referee_info):
    @debug.error_wrap('referee_info', 'name', str)
    def get_name(self):
        self._name = self.soup.select('h1 span')[0].text

    @debug.error_wrap('referee_info', 'number', int)
    def get_number(self):
        self._number = int(self.soup.find('text').text)

    @debug.error_wrap('referee_info', 'birthday', str)
    def get_birthday(self):
        birthday_raw = [x.text for x in self.soup.select('#meta p') if 'Born:' in x.text][0]
        birthday_raw = birthday_raw.replace('Born: ', '').split(' in ')[0]
        self._birthday = birthday_raw.replace('Born:\n', '').replace('\n', '').replace('   ', '')

    def _fetch(self):
        self.get_name()
        self.get_number()
        self.get_birthday()

class executive_info(abstract.executive_info):
    @debug.error_wrap('executive_info', 'teams', str)
    def get_name(self):
        self._name = self.soup.select('h1 span')[0].text

    @debug.error_wrap('executive_info', 'birthday', str)
    def get_birthday(self):
        birthday_raw = [x.text for x in self.soup.select('#meta p') if 'Born:' in x.text][0]
        birthday_raw = birthday_raw.replace('Born: ', '').split(' in ')[0]
        self._birthday = birthday_raw.replace('Born:\n', '').replace('\n', '').replace('   ', '')

    @debug.error_wrap('executive_info', 'teams', str)
    def get_teams(self):
        teams = [x.text for x in self.soup.select('tbody th+ .left') if x.text != 'TOT']
        self._teams = ','.join(list(set(teams)))

    def _fetch(self):
        self.get_name()
        self.get_birthday()
        self.get_teams()

class coach_info(abstract.coach_info):
    @debug.error_wrap('coach_info', 'name', str)
    def get_name(self):
        self._name = self.soup.select('h1 span')[0].text

    @debug.error_wrap('coach_info', 'birthday', str)
    def get_birthday(self):
        birthday_raw = [x.text for x in self.soup.select('#meta p') if 'Born:' in x.text][0]
        birthday_raw = birthday_raw.replace('Born: ', '').split(' in ')[0]
        self._birthday = birthday_raw.replace('Born:\n', '').replace('\n', '').replace('   ', '')

    @debug.error_wrap('coach_info', 'wins', int)
    def get_wins(self):
        self._wins = int(self.soup.select('.thead .right:nth-child(6)')[0].text)

    @debug.error_wrap('coach_info', 'losses', int)
    def get_losses(self):
        self._losses = int(self.soup.select('.thead .right:nth-child(7)')[0].text)

    @debug.error_wrap('coach_info', 'teams', str)
    def get_teams(self):
        teams = [x.text for x in self.soup.select('.right+ .left a') if x.text != 'TOT']
        self._teams = ','.join(list(set(teams)))

    def _fetch(self):
        self.get_name()
        self.get_birthday()
        self.get_wins()
        self.get_losses()
        self.get_teams()

class player_info(abstract.player_info):
    @debug.error_wrap('player_info', 'header', None, info = 'This may affect the shoots, birthday, draft, debut, college, and highschool fields.')
    def get_header(self):
        hand_dict = {'Left': 'L', 'Right': 'R'}

        for i in range(1,20):
            string = 'p:nth-child(' + str(i) + ')'

            try:
                text = self.soup.select(string)[0].text.replace('\n', '')
                text = text.replace('\t', '')
                text = text.replace('            ', '')
                text = text.replace('    ', '')
            except:
                break

            if 'Sports Reference' in text:
                break

            if 'Shoots:' in text:
                tmp = text.split('Shoots:')[1]
                if tmp in hand_dict.keys():
                    self._shoots = hand_dict[tmp]

            if 'Born:' in text:
                self._birthday = text.replace('Born: ', '').split('in')[0].replace(',', ', ')

            if 'Draft:' in text:
                parts = re.split(r'\(|\)', text)
                self._draft_position = int(re.findall('[0-9]{1,2}', parts[1].split(', ')[1])[0])
                self._draft_team = parts[0].replace('  ', '').replace('Draft:', '').split(',')[0]
                self._draft_year = int(re.findall('[0-9]{4}', parts[2])[0])

            if 'NBA Debut:' in text:
                self._debut_date = text.replace('NBA Debut: ', '')

            if 'College:' in text:
                self._college = 1

            if 'High School' in text:
                self._high_school = 1

    @debug.error_wrap('player_info', 'name', str)
    def get_name(self):
        self._name = self.soup.select('h1 span')[0].text

    @debug.error_wrap('player_info', 'career_seasons', str)
    def get_career_seasons(self):
        ages = self.soup.select('#per_game .full_table th+ .center')
        self._career_seasons = len(ages)

    @debug.error_wrap('player_info', 'teams', str)
    def get_teams(self):
        teams_raw = self.soup.find('table', {'id': 'per_game_stats'}).find_all('td', {'data-stat': 'team_name_abbr'})
        teams = [x.text for x in teams_raw if x.text not in ['TOT', '2TM']]
        self._teams = ','.join(list(set(teams)))

    def _fetch(self):
        self.get_header()
        self.get_name()
        self.get_career_seasons()
        self.get_teams()

class team_info(abstract.team_info):
    def __init__(self, href, pager, id_cache):
        super().__init__(href, pager, id_cache)
        if not href in id_cache.keys():
            franchise_href = '/'.join(href.split('/')[0:-1])
            self.franchise_soup = pager.get(franchise_href)

    @debug.error_wrap('team_info', 'get_hrefs', None, info = 'May affect linking up to coach and executive ids.')
    def get_hrefs(self):
        for x in self.soup.select('#meta div a'):
            if 'coaches' in x.attrs['href']:
                self._coach_href = x.attrs['href']

            if 'executives' in x.attrs['href']:
                self._executive_href = x.attrs['href']

    @debug.error_wrap('team_info', 'indexed_stats', None, info = 'Needed for wins, losses, and playoff appearances; it will still fail after this')
    def get_indexed_stats(self):
        season_text = str(self._season - 1) + '-' + str(self._season)[2:4]
        seasons_list = self.franchise_soup.select('th.left')
        franchise_index = int([i for i, x in enumerate(seasons_list) if x.text == season_text][0])
        self._wins = int(self.franchise_soup.select('.left+ .right')[franchise_index].text)
        self._losses = int(self.franchise_soup.select('.right:nth-child(5)')[franchise_index].text)
        text = self.franchise_soup.select('.right+ .left')[franchise_index].text
        self._playoff_appearance = text != ''

    @debug.error_wrap('team_info', 'indexed_stats', None, info = 'Needed for season and abbreviation; it will still fail after this')
    def get_url_based_stats(self):
        url = self.soup.find('link', {'rel': 'canonical'}).attrs['href']
        self._season = int(url.split('/')[5].replace('.html', ''))
        self._abbreviation = url.split('/')[4]

    @debug.error_wrap('team_info', 'name', str)
    def get_name(self):
        beginning = re.sub(' Roster.*$', '', self.soup.title.text)
        self._name = re.sub('^[0-9]{4}-[0-9]{2} ', '', beginning)

    @debug.error_wrap('team_info', 'location', str)
    def get_location(self):
        m = self.franchise_soup.select('h1+ p')[0].text
        self._location = m.replace('\n', '').replace('Location:  ', '')

    def _fetch(self):
        self.get_hrefs()
        # must go before indexed_stats
        self.get_url_based_stats()
        self.get_indexed_stats()
        self.get_name()
        self.get_location()

class season_info(abstract.season_info):
    def __init__(self, href, pager, id_cache):
        super().__init__(href, pager, id_cache)
        if not href in id_cache.keys():
            tabs = self.soup.find('div', {'id': 'inner_nav'})
            links = tabs.find('ul', {'class': 'hoversmooth'}).find_all('a')
            self.playoffs_soup = pager.get(links[-1].attrs['href'])

            schedule = [x for x in links if 'Schedule and Results' in x.text][0]
            initial_page = pager.get(schedule.attrs['href'])
            months = initial_page.find('div', {'class': 'filter'}).find_all('a')
            self.schedule_soups = [pager.get(x.attrs['href']) for x in months]

            rankings = [x for x in links if 'Standings' == x.text][0]
            self.rankings_soup = pager.get(rankings.attrs['href'])

    @debug.error_wrap('season_info', 'header', None, info = 'This will affect the champion team.')
    def get_header(self):
        for line in self.soup.select('#meta p'):
            if 'League Champion' in line.text:
                self._champion_href = line.find('a').attrs['href']

    @debug.error_wrap('season_info', 'awards', None, info = 'This will affect just about all awards outside of the champion and finals mvp.')
    def get_awards(self):
        comments = self.soup.find_all(string=lambda t: isinstance(t, Comment))
        comment = [x for x in comments if 'award' in x][0]
        new_soup = BeautifulSoup(comment.replace('\n', ''), features = 'lxml')
        all = [x for x in new_soup.select('#all_awards a') if x.text != '']
        players = [all[i] for i in range(len(all)) if i %2 == 1]
        
        self._mvp_href = players[0].attrs['href']
        self._roty_href = players[1].attrs['href']
        self._dpoy_href = players[2].attrs['href']
        self._mip_href = players[3].attrs['href']
        self._sixmoty_href = players[4].attrs['href']

    @debug.error_wrap('season_info', 'season', str)
    def get_season(self):
        self._season = int(self.soup.select('h1 span')[0].text.split('-')[0]) + 1

    @debug.error_wrap('season_info', 'games', int)
    def get_games(self):
        team_totals = [int(x.text) for x in self.soup.select('#per_game-team tbody .left+ .right')]
        self._games = sum(team_totals) / 2

    @debug.error_wrap('season_info', 'teams', int)
    def get_teams(self):
        teams = self.soup.select('#per_game-team a')
        self._teams = len(teams)

    @debug.error_wrap('season_info', 'finals_mvp_href', int, info = 'This will affect the player ID of the finals mvp.')
    def get_finals_mvp_href(self):
        all_p = self.playoffs_soup.find('div', {'id': 'meta'}).find_all('p')
        selection = [x.find('a') for x in all_p if 'Finals MVP' in x.text][0]
        self._finals_mvp_href = selection.attrs['href']

    def get_rankings(self):
        comments = self.rankings_soup.find_all(string=lambda t: isinstance(t, Comment))
        raw = [x for x in comments if 'expanded_standings' in x][0]
        table = BeautifulSoup(raw.replace('\n', ''), features = 'lxml')
        rows = table.find('tbody').find_all('tr')
        output = {}
        for row in rows:
            href = row.find('a').attrs['href']
            rank = int(row.find(attrs = {'data-stat': 'ranker'}).text)
            output[href] = rank

        self._rankings = output

    def get_schedule(self):
        for page in self.schedule_soups:
            table = page.find('table', {'id': 'schedule'})
            box_scores = table.find_all('td', {'data-stat': 'box_score_text'})
            self._schedule += [x.find('a').attrs['href'] for x in box_scores]

    def _fetch(self):
        self.get_rankings()
        self.get_schedule()
        self.get_season()
        self.get_header()
        self.get_awards()
        self.get_games()
        self.get_teams()
        self.get_finals_mvp_href()

class game_info(abstract.game_info):
    @debug.error_wrap('game_info', 'game_setup', str)
    def game_setup(self):
        scorebox = self.soup.find('div', {'class': 'scorebox'})
        teams = [x.find('a') for x in scorebox.find_all('strong')]

        self._home_team_name = teams[1].text
        self._home_team_href = teams[1].attrs['href']
        self._away_team_name = teams[0].text
        self._away_team_href = teams[0].attrs['href']

        self._attendance = 0
        self._duration = 0
        self._referee_hrefs = ''

        self.heading = self.soup.select('h1')[0].text

        for line in self.soup.select('#content > div')[-2].find_all('div'):

            if 'Attendance' in line.text:
                self._attendance = int(line.contents[1].replace(',', ''))

            if 'Time of Game' in line.text:
                selection = line.contents[1].split(':')
                hours = int(selection[0])
                minutes = int(selection[1])
                self._duration = hours * 60 + minutes

            if 'Officials' in line.text:
                selection = line.select('a')
                self._referee_hrefs = [tag.attrs['href'] for tag in selection]

    @debug.error_wrap('game_info', 'type', bool, info = 'Not sure about game type; regular season is assumed.')
    def get_type(self):
        try:
            heading = self.heading
        except:
            self.game_setup()
            heading = self.heading

        if ('NBA' in heading) and (':' in heading):
            self._type = 'playoffs'
            self._playoffs = True
            self._season_tournament = False
            self._play_in = False
        elif 'In-Season' in heading:
            self._type = 'in-season tournament'
            self._playoffs = False
            self._season_tournament = True
            self._play_in = False
        elif 'Play-In Game' in heading:
            self._type = 'play-in'
            self._playoffs = False
            self._season_tournament = False
            self._play_in = True
        else:
            self._type = 'regular'

    @debug.error_wrap('game_info', 'date', str)
    def get_date(self):
        self._date = re.split('[a-z], ', self.soup.title.text)[1].split(' | ')[0]

    @debug.error_wrap('game_info', 'location', str)
    def get_location(self):
        self._location = self.soup.select('.scorebox_meta div')[1].text

    @debug.error_wrap('game_info', 'season', int)
    def get_season(self):
        self._season = int(self.soup.select('u')[1].text.split('-')[0]) + 1

    def _fetch(self):
        self.game_setup()
        self.get_type()
        self.get_date()
        self.get_location()
        self.get_season()

class game_data(abstract.game_data):
    @staticmethod
    def initialize_table() -> dict:
        return {'Quarter': [],
                'Seconds': [],
                'Threes': [],
                'Three_Attempts': [],
                'Twos': [],
                'Two_Attempts': [],
                'Freethrows': [],
                'Freethrow_Attempts': [],
                'Offensive_Rebounds': [],
                'Deffensive_Rebounds': [],
                'Assists': [],
                'Steals': [],
                'Blocks': [],
                'Turnovers': [],
                'Fouls': [],
                'Points': [],
                'PM': [],
                'Win': [],
                'Home': [],
                'Injured': [],
                'Player_ID': [],
                'Game_ID': [],
                'Season': [],
                'Team_ID': [],
                'Opponent_ID': []}

    def parse_row(self, row_soup) -> dict:
        data_stats = {'Seconds': 'mp',
                      'Threes': 'fg3',
                      'Three_Attempts': 'fg3a',
                      'Twos': 'fg',
                      'Two_Attempts': 'fga',
                      'Freethrows': 'ft',
                      'Freethrow_Attempts': 'fta',
                      'Offensive_Rebounds': 'orb',
                      'Deffensive_Rebounds': 'drb',
                      'Assists': 'ast',
                      'Steals': 'stl',
                      'Blocks': 'blk',
                      'Turnovers': 'tov',
                      'Fouls': 'pf',
                      'Points': 'pts',
                      'PM': 'plus_minus',
                      'Player_ID': 'player'}

        output = self.initialize_table()
        for key, stat in data_stats.items():
            match stat:
                case 'player':
                    try:
                        data = row_soup.find('th', {'data-stat': stat})
                        output[key] = [data.find('a').attrs['href']]
                    except:
                        # Needed for team totals
                        output[key] = ['']

                case 'mp':
                    try:
                        t = row_soup.find('td', {'data-stat': stat}).text
                        m = abs(int(t.split(':')[0]))
                        s = abs(int(t.split(':')[1]))
                        output[key] = [60*m + s]
                    except AttributeError:
                        # Sometimes needed for a player that didn't play
                        output[key] = [0]
                    except:
                        # Needed for whole minute times
                        t = row_soup.find('td', {'data-stat': stat}).text
                        m = int(t)
                        output[key] = [abs(60*m)]

                case 'plus_minus':
                    try:
                        text = row_soup.find('td', {'data-stat': stat}).text
                        output[key] = [int(text.replace('+', ''))]
                    except:
                        output[key] = [0]

                case _:
                    try:
                        t = row_soup.find('td', {'data-stat': stat}).text
                        output[key] = [abs(int(t))]
                    except:
                        output[key] = [0]

        return output

    def injury_check(self, row_soup, t_href) -> bool:
        try:
            reason = row_soup.find('td', {'data-stat': 'reason'})
        except:
            return False

        if isinstance(reason, type(None)):
            return False
        else:
            self._injured[t_href].append(row_soup.find('a').attrs['href'])
            return True

    def parse_table(self, table_soup, t_href, o_href) -> dict:
        try:
            e = table_soup.find('thead').extract()
            e = [x.extract() for x in table_soup.find_all('tr', {'class': 'thead'})]
            del e
        except:
            pass

        whole_game = re.compile(r'^.*-game-basic$')
        quarter = re.compile(r'^.*q[1-4]-basic$')
        id_string = table_soup.attrs['id']
        if whole_game.match(id_string):
            period = 'whole'
        else:
            tmp = id_string.split('-')[2]
            if quarter.match(id_string):
                period = int(tmp.replace('q', ''))
            else:
                period = int(tmp.replace('ot', '')) + 4

        rows = []
        for row in table_soup.find_all('tr'):
            if not self.injury_check(row, t_href):
                parsed = self.parse_row(row)
                parsed['Injured'] = [False]

                if t_href == self._home_team_href:
                    parsed['Win'] = [self._home_win]
                    parsed['Home'] = [True]
                else:
                    parsed['Win'] = [not self._home_win]
                    parsed['Home'] = [False]

                parsed['Season'] = [self._season]
                parsed['Team_ID'] = [t_href]
                parsed['Opponent_ID'] = [o_href]
                parsed['Game_ID'] = [self._game_href]
                parsed['Quarter'] = [period]
                rows.append(parsed)

        output = {}
        for key in rows[0]:
            try:
                output[key] = [x[key][0] for x in rows]
            except:
                output[key] = [0]

        return output

    def append_table(self, table):
        players = table.copy()
        team = table.copy()
        del team['PM']
        del team['Injured']
        del team['Player_ID']

        if 'whole' in table['Quarter']:
            del players['Quarter']
            del team['Quarter']

            for key, value in players.items():
                tmp = self._player_data[key] + value[:-1]
                self._player_data.update({key: tmp})

            for key, value in team.items():
                tmp = self._team_data[key] + [value[-1]]
                self._team_data.update({key: tmp})
        else:
            for key, value in players.items():
                tmp = self._player_data_quarters[key] + value[:-1]
                self._player_data_quarters.update({key: tmp})

            for key, value in team.items():
                tmp = self._team_data_quarters[key] + [value[1]]
                self._team_data_quarters.update({key: tmp})

    def get_header(self):
        header = self.soup.find('div', {'class': 'scorebox'})
        items = header.find_all('strong')
        links = [x.find('a').attrs['href'] for x in items]

        # The second to last is the away team
        self._away_team_href = links[0]
        self._away_abbrev = self._away_team_href.split('/')[2]
        self._injured[self._away_team_href] = []

        # The last will be the home team
        self._home_team_href = links[1]
        self._home_abbrev = self._home_team_href.split('/')[2]
        self._injured[self._home_team_href] = []

        self._season = self._home_team_href.split('/')[-1].split('.')[0]

        game_url = self.soup.find('link', {'rel': 'canonical'}).attrs['href']
        self._game_href = game_url.split('com')[1]

    def get_footer(self):
        foot = self.soup.select('#content > div')[-2].find_all('div')

        for line in foot:
            if 'Attendance' in line.text:
                self.Attendance = int(line.contents[1].replace(',', ''))

            elif 'Time of Game' in line.text:
                selection = line.contents[1].split(':')
                hours = int(selection[0])
                minutes = int(selection[1])
                self.Duration = hours * 60 + minutes

            elif 'Officials' in line.text:
                selection = line.select('a')
                self.Referee_Names = [tag.text for tag in selection]
                self.Referee_hrefs = [tag.attrs['href'] for tag in selection]

            elif 'Inactive' in line.text:
                for tag in list(line.children):
                    if tag.name == 'span':
                        team = tag.text
                    if tag.name == 'a':
                        if team == self._home_abbrev:
                            self._injured[self._home_team_href].append(tag.attrs['href'])
                        else:
                            self._injured[self._away_team_href].append(tag.attrs['href'])

                do_not_catch = [',', 'Inactive:']
                strip = [x.text.strip() for x in list(line.children)]
                m = re.compile(r'[A-Z]{3}')
                children = [x for x in strip if not (x in do_not_catch or m.match(x))]
                injured = line.find_all('a')
                self.Injured = [x.text for x in injured]
                self.Injured_dict = {x.text.strip(): x.attrs['href'] for x in injured}

    def get_home_win(self):
        raw = self.soup.find('div', {'class': 'scorebox'})
        scores = [int(x.text) for x in raw.find_all('div', {'class': 'score'})]
        self._home_win = scores[0] < scores[1]

    def get_tables(self):
        clean_table = self.initialize_table()

        team_data = clean_table.copy()
        del team_data['PM']
        del team_data['Injured']
        del team_data['Player_ID']
        self._team_data_quarters = team_data.copy()
        del team_data['Quarter']
        self._team_data = team_data.copy()

        player_data = clean_table.copy()
        self._player_data_quarters = player_data.copy()
        del player_data['Quarter']
        self._player_data = player_data.copy()

        adv = re.compile(r'^.*advanced$')
        half = re.compile(r'^box-[A-Z]*-h[1-2].*$')
        table_ids = [x.attrs['id'] for x in self.soup.find_all('table')]
        tables = [x for x in table_ids if not adv.match(x) and not half.match(x)]

        for table in tables:
            match table.split('-')[1]:
                case self._home_abbrev:
                    team_href = self._home_team_href
                    opponent_href = self._away_team_href
                case _:
                    team_href = self._away_team_href
                    opponent_href = self._home_team_href

            t = self.soup.find('table', {'id': table})
            parsed_table = self.parse_table(t, team_href, opponent_href)
            self.append_table(parsed_table.copy())

    def _fetch(self):
        self.get_header()
        self.get_footer()
        self.get_home_win()
        self.get_tables()

class BasketballReferenceEngine(abstract.engine):
    def __init__(self, pager, database):
        super().__init__(pager, database)
        self._source = "basketball_reference"

    def get_id_cache(self):
        con = self.database.give_connection()
        cur = con.cursor()

        cols = ["basketball_reference", "value"]
        locations = [("referee_info", self.referee_id_cache), 
                     ("executive_info", self.executive_id_cache),
                     ("coach_info", self.coach_id_cache),
                     ("player_info", self.player_id_cache),
                     ("team_info", self.team_id_cache),
                     ("season_info", self.season_id_cache),
                     ("game_info", self.game_id_cache),
                     ("game_data", self.game_data_cache),
                     ("rankings", self.rankings)]

        for location, cache in locations:
            query = f"SELECT {','.join(cols)} FROM id_cache WHERE type = '{location}'"
            tmp = cur.execute(query)
            from_cache = {href: value for href, value in cur.fetchall()}
            cache.update(from_cache)

        cur.close()
        con.close()

        self.referee_max_id = max([0] + list(self.referee_id_cache.values()))
        self.executive_max_id = max([0] + list(self.executive_id_cache.values()))
        self.coach_max_id = max([0] + list(self.coach_id_cache.values()))
        self.player_max_id = max([0] + list(self.player_id_cache.values()))
        self.team_max_id = max([0] + list(self.team_id_cache.values()))
        self.game_max_id = max([0] + list(self.game_id_cache.values()))

    def referee_info(self, href) -> referee_info:
        return referee_info(href, self.pager, self.referee_id_cache)

    def executive_info(self, href) -> executive_info:
        return executive_info(href, self.pager, self.executive_id_cache)

    def coach_info(self, href) -> coach_info:
        return coach_info(href, self.pager, self.coach_id_cache)

    def player_info(self, href) -> player_info:
        return player_info(href, self.pager, self.player_id_cache)

    def team_info(self, href) -> team_info:
        return team_info(href, self.pager, self.team_id_cache)

    def season_info(self, href) -> season_info:
        return season_info(href, self.pager, self.season_id_cache)

    def game_info(self, href) -> game_info:
        return game_info(href, self.pager, self.game_id_cache)

    def game_data(self, href) -> game_data:
        return game_data(href, self.pager)
