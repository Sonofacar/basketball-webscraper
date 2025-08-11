from abc import abstractmethod
from debug import debug
from functools import wraps

# List of classes:
# [x] referee_info
# [x] executive_info
# [x] coach_info
# [x] player_info
# [x] team_info
# [x] season_info
# [x] game_info
# [x] game_data
#   [ ] player_game
#   [ ] player_querterly
#   [ ] team_game
#   [ ] team_quarterly

def require_fetch(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not getattr(self, '_fetched', False):
            self.fetch()
        return func(self, *args, **kwargs)
    return wrapper

class referee_info(debug):
    def __init__(self, href, pager, id_cache):
        self.href = href
        if href in id_cache.keys():
            self._id = id_cache[href]
            self._fetched = True
        else:
            self.soup = pager.get(href)
            self._name = None
            self._number = None
            self._birthday = None
            self._id = None
            self._fetched = False

    @abstractmethod
    def _fetch(self):
        pass

    @property
    @require_fetch
    def name(self):
        return self._name

    @property
    @require_fetch
    def number(self):
        return self._number

    @property
    @require_fetch
    def birthday(self):
        return self._birthday

    @property
    @require_fetch
    def id(self):
        return self._id

    @debug.error_wrap('referee_info', 'referee_id', int)
    def gen_id(self, prev):
        self._id = prev + 1

    @property
    @require_fetch
    def output(self):
        return self._output

    def fetch(self, prev = 0):
        if self._fetched:
            return # Already fetched
        self.gen_id(prev)
        self._fetch()
        self._fetched = True
        self._output = {'Name': [self.name],
                        'Number': [self.number],
                        'Birthday': [self.birthday],
                        'Referee_ID': [self.id]}

class executive_info(debug):
    def __init__(self, href, pager, id_cache):
        self.href = href
        if href in id_cache.keys():
            self._id = id_cache[href]
            self._fetched = True
        else:
            self.soup = pager.get(href)
            self._name = None
            self._birthday = None
            self._teams = None
            self._id = None
            self._fetched = False

    @abstractmethod
    def _fetch(self):
        pass

    @property
    @require_fetch
    def name(self):
        return self._name

    @property
    @require_fetch
    def birthday(self):
        return self._birthday

    @property
    @require_fetch
    def teams(self):
        return self._teams

    @property
    @require_fetch
    def id(self):
        return self._id

    @property
    @require_fetch
    def output(self):
        return self._output

    @debug.error_wrap('executive_info', 'executive_id', str)
    def gen_id(self, prev):
        self._id = prev + 1

    def fetch(self, prev = 0):
        if self._fetched:
            return # Already fetched
        self.gen_id(prev)
        self._fetch()
        self._fetched = True
        self._output = {'Name': [self.name],
                        'Birthday': [self.birthday],
                        'Teams': [self.teams],
                        'Executive_ID': [self.id]}

class coach_info(debug):
    def __init__(self, href, pager, id_cache):
        self.href = href
        if href in id_cache.keys():
            self._id = id_cache[href]
            self._fetched = True
        else:
            self.soup = pager.get(href)
            self._name = None
            self._birthday = None
            self._wins = None
            self._losses = None
            self._teams = None
            self._id = None
            self._fetched = False

    @abstractmethod
    def _fetch(self):
        pass

    @property
    @require_fetch
    def name(self):
        return self._name

    @property
    @require_fetch
    def birthday(self):
        return self._birthday

    @property
    @require_fetch
    def wins(self):
        return self._wins

    @property
    @require_fetch
    def losses(self):
        return self._losses

    @property
    @require_fetch
    def teams(self):
        return self._teams

    @property
    @require_fetch
    def id(self):
        return self._id

    @debug.error_wrap('coach_info', 'coach_id', int)
    def gen_id(self, prev):
        self._id = prev + 1

    @property
    @require_fetch
    def output(self):
        return self._output

    def fetch(self, prev = 0):
        if self._fetched:
            return # Already fetched
        self.gen_id(prev)
        self._fetch()
        self._fetched = True
        self._output = {'Name': [self.name],
                        'Birthday': [self.birthday],
                        'Wins': [self.wins],
                        'Losses': [self.losses],
                        'Teams': [self.teams],
                        'Executive_ID': [self.id]}

class player_info(debug):
    def __init__(self, href, pager, id_cache):
        self.href = href
        if href in id_cache.keys():
            self._id = id_cache[href]
            self._fetched = True
        else:
            self.soup = pager.get(href)
            self._name = None
            self._shoots = None
            self._birthday = None
            self._high_school = None
            self._college = None
            self._draft_position = None
            self._draft_team = None
            self._draft_year = None
            self._debut_date = None
            self._career_seasons = None
            self._teams = None
            self._id = None
            self._fetched = False

    @abstractmethod
    def _fetch(self):
        pass

    @property
    @require_fetch
    def name(self):
        return self._name

    @property
    @require_fetch
    def shoots(self):
        return self._shoots

    @property
    @require_fetch
    def birthday(self):
        return self._birthday

    @property
    @require_fetch
    def high_school(self):
        return self._high_school

    @property
    @require_fetch
    def college(self):
        return self._college

    @property
    @require_fetch
    def draft_position(self):
        return self._draft_position

    @property
    @require_fetch
    def draft_team(self):
        return self._draft_team

    @property
    @require_fetch
    def draft_year(self):
        return self._draft_year

    @property
    @require_fetch
    def debut_date(self):
        return self._debut_date

    @property
    @require_fetch
    def career_seasons(self):
        return self._career_seasons

    @property
    @require_fetch
    def teams(self):
        return self._teams

    @property
    @require_fetch
    def id(self):
        return self._id

    def gen_id(self, prev):
        self._id = prev + 1

    @property
    @require_fetch
    def output(self):
        return self._output

    def fetch(self, prev = 0):
        if self._fetched:
            return # Already fetched
        self.gen_id(prev)
        self._fetch()
        self._fetched = True
        self._output = {'Name': [self.name],
                        'Shoots': [self.shoots],
                        'Birthday': [self.birthday],
                        'High_School': [self.high_school],
                        'College': [self.college],
                        'Draft_Position': [self.draft_position],
                        'Draft_Team': [self.draft_team],
                        'Draft_Year': [self.draft_year],
                        'Debut_Date': [self.debut_date],
                        'Career_Seasons': [self.career_seasons],
                        'Teams': [self.teams],
                        'Player_ID': [self.id]}

class team_info(debug):
    def __init__(self, href, pager, id_cache):
        self.href = href
        if href in id_cache.keys():
            self._id = id_cache[href]
            self._fetched = True
        else: 
            self.soup = pager.get(href)
            self._name = None
            self._abbreviation = None
            self._wins = None
            self._losses = None
            self._location = None
            self._playoff_appearance = None
            self._ranking = None
            self._id = None
            self._season = None
            self._executive = None
            self._executive_href = None
            self._coach = None
            self._coach_href = None
            self._fetched = False

    @abstractmethod
    def _fetch(self):
        pass

    @property
    @require_fetch
    def name(self):
        return self._name

    @property
    @require_fetch
    def abbreviation(self):
        return self._abbreviation

    @property
    @require_fetch
    def wins(self):
        return self._wins

    @property
    @require_fetch
    def losses(self):
        return self._losses

    @property
    @require_fetch
    def location(self):
        return self._location

    @property
    @require_fetch
    def playoff_appearance(self):
        return self._playoff_appearance

    @property
    @require_fetch
    def ranking(self):
        return self._ranking

    @property
    @require_fetch
    def season(self):
        return self._season

    @property
    @require_fetch
    def executive(self):
        return self._executive

    @executive.setter
    def executive(self, value):
        self._executive = value

    @property
    @require_fetch
    def executive_href(self):
        return self._executive_href

    @property
    @require_fetch
    def coach(self):
        return self._coach

    @coach.setter
    def coach(self, value):
        self._coach = value

    @property
    @require_fetch
    def coach_href(self):
        return self._coach_href

    @property
    @require_fetch
    def id(self):
        return self._id

    def gen_id(self, prev):
        self._id = prev + 1

    @property
    @require_fetch
    def output(self):
        return self._output

    def refresh_output(self):
        self._output = {'Name': [self.name],
                        'Abbreviation': [self.abbreviation],
                        'Wins': [self.wins],
                        'Losses': [self.losses],
                        'Location': [self.location],
                        'Playoff_Appearance': [self.playoff_appearance],
                        'League_Ranking': [self.ranking],
                        'Team_ID': [self.id],
                        'Season': [self.season],
                        'Executive_ID': [self.executive],
                        'Coach_ID': [self.coach]}

    def fetch(self, prev = 0):
        if self._fetched:
            return # Already fetched
        self.gen_id(prev)
        self._fetch()
        self._fetched = True
        self.refresh_output()

class season_info(debug):
    def __init__(self, href, pager, id_cache):
        self.href = href
        if href in id_cache.keys():
            self._season = id_cache[href]
            self._fetched = True
        else: 
            self.soup = pager.get(href)
            self._season = None
            self._games = None
            self._teams = None
            self._champion = None
            self._champion_href = None
            self._finals_mvp = None
            self._finals_mvp_href = None
            self._mvp = None
            self._mvp_href = None
            self._dpoy = None
            self._dpoy_href = None
            self._mip = None
            self._mip_href = None
            self._sixmoty = None
            self._sixmoty_href = None
            self._roty = None
            self._roty_href = None
            self._schedule = []
            self._rankings = None
            self._fetched = False

    @abstractmethod
    def _fetch(self):
        pass

    @property
    @require_fetch
    def season(self):
        return self._season

    @property
    @require_fetch
    def games(self):
        return self._games

    @property
    @require_fetch
    def teams(self):
        return self._teams

    @property
    @require_fetch
    def champion(self):
        return self._champion

    @champion.setter
    def champion(self, value):
        self._champion = value

    @property
    @require_fetch
    def champion_href(self):
        return self._champion_href

    @property
    @require_fetch
    def finals_mvp(self):
        return self._finals_mvp

    @finals_mvp.setter
    def finals_mvp(self, value):
        self._finals_mvp = value

    @property
    @require_fetch
    def finals_mvp_href(self):
        return self._finals_mvp_href

    @property
    @require_fetch
    def mvp(self):
        return self._mvp

    @mvp.setter
    def mvp(self, value):
        self._mvp = value

    @property
    @require_fetch
    def mvp_href(self):
        return self._mvp_href

    @property
    @require_fetch
    def dpoy(self):
        return self._dpoy

    @dpoy.setter
    def dpoy(self, value):
        self._dpoy = value

    @property
    @require_fetch
    def dpoy_href(self):
        return self._dpoy_href

    @property
    @require_fetch
    def mip(self):
        return self._mip

    @mip.setter
    def mip(self, value):
        self._mip = value

    @property
    @require_fetch
    def mip_href(self):
        return self._mip_href

    @property
    @require_fetch
    def sixmoty(self):
        return self._sixmoty

    @sixmoty.setter
    def sixmoty(self, value):
        self._sixmoty = value

    @property
    @require_fetch
    def sixmoty_href(self):
        return self._sixmoty_href

    @property
    @require_fetch
    def roty(self):
        return self._roty

    @roty.setter
    def roty(self, value):
        self._roty = value

    @property
    @require_fetch
    def roty_href(self):
        return self._roty_href

    @property
    @require_fetch
    def output(self):
        return self._output

    @property
    @require_fetch
    def schedule(self):
        return self._schedule

    @property
    @require_fetch
    def rankings(self):
        return self._rankings

    def refresh_output(self):
        self._output = {'Season': [self.season],
                        'Games': [self.games],
                        'Teams': [self.teams],
                        'Champion': [self.champion],
                        'Finals_MVP': [self.finals_mvp],
                        'MVP': [self.mvp],
                        'DPOY': [self.dpoy],
                        'MIP': [self.mip],
                        'SixMOTY': [self.sixmoty],
                        'ROTY': [self.roty]}

    def fetch(self):
        if self._fetched:
            return # Already fetched
        self._fetch()
        self._fetched = True
        self.refresh_output()

class game_info(debug):
    def __init__(self, href, pager, id_cache):
        self.href = href
        if href in id_cache.keys():
            self._id = id_cache[href]
            self._fetched = True
        else: 
            self.soup = pager.get(href)
            self._home_team_name = None
            self._home_team_href = None
            self._away_team_name = None
            self._away_team_href = None
            self._date = None
            self._location = None
            self._duration = None
            self._attendance = None
            self._id = None
            self._home_team_id = None
            self._away_team_id = None
            self._season = None
            self._playoffs = None
            self._in_season_tournament = None
            self._play_in = None
            self._referee_ids = [None, None, None]
            self._referee_hrefs = [None, None, None]
            self._fetched = False
            self._type = 'regular'

    @abstractmethod
    def _fetch(self):
        pass

    @property
    @require_fetch
    def home_team_name(self):
        return self._home_team_name

    @property
    @require_fetch
    def home_team_href(self):
        return self._home_team_href

    @property
    @require_fetch
    def away_team_name(self):
        return self._away_team_name

    @property
    @require_fetch
    def away_team_href(self):
        return self._away_team_href

    @property
    @require_fetch
    def date(self):
        return self._date

    @property
    @require_fetch
    def location(self):
        return self._location

    @property
    @require_fetch
    def duration(self):
        return self._duration

    @property
    @require_fetch
    def attendance(self):
        return self._attendance

    @property
    @require_fetch
    def home_team_id(self):
        return self._home_team_id

    @home_team_id.setter
    def home_team_id(self, value):
        self._home_team_id = value

    @property
    @require_fetch
    def away_team_id(self):
        return self._away_team_id

    @away_team_id.setter
    def away_team_id(self, value):
        self._away_team_id = value

    @property
    @require_fetch
    def season(self):
        return self._season

    @property
    @require_fetch
    def playoffs(self):
        return self._playoffs

    @property
    @require_fetch
    def referee_ids(self):
        return self._referee_ids

    @referee_ids.setter
    def referee_ids(self, values):
        for i in range(len(self._referee_ids)):
            try:
                self._referee_ids[i] = values[i]
            except:
                continue

    @property
    @require_fetch
    def referee_hrefs(self):
        return self._referee_hrefs

    @property
    @require_fetch
    def playoffs(self):
        return self._playoffs

    @property
    @require_fetch
    def in_season_tournament(self):
        return self._in_season_tournament

    @property
    @require_fetch
    def play_in(self):
        return self._play_in

    @property
    @require_fetch
    def id(self):
        return self._id

    def gen_id(self, prev):
        self._id = prev + 1

    @property
    @require_fetch
    def output(self):
        return self._output

    def refresh_output(self):
        self._output = {'Home_Team_Name': [self.home_team_name],
                        'Away_Team_Name': [self.away_team_name],
                        'Date': [self.date],
                        'Location': [self.location],
                        'Duration': [self.duration],
                        'Attendance': [self.attendance],
                        'Game_ID': [self.id],
                        'Home_Team_ID': [self.home_team_id],
                        'Away_Team_ID': [self.away_team_id],
                        'Season': [self.season],
                        'Playoffs': [self.playoffs],
                        'In_Season_Tournament': [self.in_season_tournament],
                        'Play_In': [self.play_in],
                        'Referee_ID1': [self.referee_ids[0]],
                        'Referee_ID2': [self.referee_ids[1]],
                        'Referee_ID3': [self.referee_ids[2]]}

    def fetch(self, prev = 0):
        if self._fetched:
            return # Already fetched
        self.gen_id(prev)
        self._fetch()
        self._fetched = True
        self.refresh_output()

class game_data(debug):
    def __init__(self, href, pager):
        self.soup = pager.get(href)
        self.href = href
        self._injured = {}
        self._home_team_href = None
        self._home_abbrev = None
        self._away_team_href = None
        self._away_abbrev = None
        self._game_href = None
        self._season = None
        self._player_data = None
        self._player_data_quarters = None
        self._team_data = None
        self._team_data_quarters = None
        self._home_win = None
        self._fetched = False

    @abstractmethod
    def _fetch(self):
        pass

    @property
    @require_fetch
    def player_data(self):
        return self._player_data

    @property
    @require_fetch
    def player_data_quarters(self):
        return self._player_data_quarters

    @property
    @require_fetch
    def team_data(self):
        return self._team_data

    @property
    @require_fetch
    def team_data_quarters(self):
        return self._team_data_quarters

    def fetch(self):
        if self._fetched:
            return # Already fetched
        self._fetch()
        self._fetched = True

def empty_href_wrap(function):
    def wrapper(self, *args, **kwargs):
        try:
            href = kwargs['href']
        except:
            href = args[0]
        if not href == None:
            return function(self, *args, **kwargs)
    return wrapper

class engine(debug):
    def __init__(self):
        self.referee_max_id = 0
        self.executive_max_id = 0
        self.coach_max_id = 0
        self.player_max_id = 0
        self.team_max_id = 0
        self.game_max_id = 0
        self.referee_id_cache = {}
        self.executive_id_cache = {}
        self.coach_id_cache = {}
        self.player_id_cache = {}
        self.team_id_cache = {}
        self.season_id_cache = {}
        self.game_id_cache = {}
        self.rankings = {}

    def save(self, data, location):
        match location:
            case 'referee_info':
                pass

            case 'executive_info':
                pass

            case 'coach_info':
                pass

            case 'player_info':
                pass

            case 'team_info':
                pass

            case 'season_info':
                pass

            case 'game_info':
                pass

            case 'game_data':
                pass

    @staticmethod
    def safe_set_id(obj):
        if obj == None:
            return None
        else:
            return obj.id

    def link_game_data(self, table, pager):
        tmp = [self.get_game_info(x, pager) for x in table['Game_ID']]
        ids = [self.safe_set_id(x) for x in tmp]
        table.update({'Game_ID': ids})

        tmp = [self.get_team_info(x, pager) for x in table['Team_ID']]
        ids = [self.safe_set_id(x) for x in tmp]
        table.update({'Team_ID': ids})

        tmp = [self.get_team_info(x, pager) for x in table['Opponent_ID']]
        ids = [self.safe_set_id(x) for x in tmp]
        table.update({'Opponent_ID': ids})

        if 'Player_ID' in table.keys():
            tmp = [self.get_player_info(x, pager) for x in table['Player_ID']]
            ids = [self.safe_set_id(x) for x in tmp]
            table.update({'Player_ID': ids})

    def get_links(self, obj, pager):
        if issubclass(obj.__class__, team_info):
            executive = self.get_executive_info(obj.executive_href, pager)
            obj.executive = self.safe_set_id(executive)
            coach = self.get_coach_info(obj.coach_href, pager)
            obj.coach = self.safe_set_id(coach)
            rank = self.rankings.get(obj.href, None)
            obj.refresh_output()

        elif issubclass(obj.__class__, season_info):
            champion = self.get_team_info(obj.champion_href, pager)
            obj.champion = self.safe_set_id(champion)
            finals_mvp = self.get_player_info(obj.finals_mvp_href, pager)
            obj.finals_mvp = self.safe_set_id(finals_mvp)
            mvp = self.get_player_info(obj.mvp_href, pager)
            obj.mvp = self.safe_set_id(mvp)
            dpoy = self.get_player_info(obj.dpoy_href, pager)
            obj.dpoy = self.safe_set_id(dpoy)
            mip = self.get_player_info(obj.mip_href, pager)
            obj.mip = self.safe_set_id(mip)
            sixmoty = self.get_player_info(obj.sixmoty_href, pager)
            obj.sixmoty = self.safe_set_id(sixmoty)
            roty = self.get_player_info(obj.roty_href, pager)
            obj.roty = self.safe_set_id(roty)
            obj.refresh_output()

            games = [self.get_game_data(x, pager) for x in obj.schedule]

        elif issubclass(obj.__class__, game_info):
            home = self.get_team_info(obj.home_team_href, pager)
            obj.home_team_id = self.safe_set_id(home)
            away = self.get_team_info(obj.away_team_href, pager)
            obj.away_team_id = self.safe_set_id(away)
            refs = [self.get_referee_info(x, pager) for x in obj.referee_hrefs]
            ref_ids = [self.safe_set_id(x) for x in refs]
            obj.referee_ids = ref_ids
            obj.refresh_output()

        elif issubclass(obj.__class__, game_data):
            self.link_game_data(obj.team_data, pager)
            self.link_game_data(obj.player_data, pager)
            self.link_game_data(obj.team_data_quarters, pager)
            self.link_game_data(obj.player_data_quarters, pager)

    @abstractmethod
    def referee_info(self, href, pager) -> referee_info:
        pass

    @empty_href_wrap
    def get_referee_info(self, href, pager):
        info = self.referee_info(href, pager)
        if not info.href in self.referee_id_cache.keys():
            info.fetch(self.referee_max_id)
            self.referee_id_cache.update({info.href: info.id})
            self.referee_max_id += 1
            self.save(info, 'referee_info')
        return info

    @abstractmethod
    def executive_info(self, href, pager) -> executive_info:
        pass

    @empty_href_wrap
    def get_executive_info(self, href, pager):
        info = self.executive_info(href, pager)
        if not info.href in self.executive_id_cache.keys():
            info.fetch(self.executive_max_id)
            self.executive_id_cache.update({info.href: info.id})
            self.executive_max_id += 1
            self.save(info.output, 'executive_info')
        return info

    @abstractmethod
    def coach_info(self, href, pager) -> coach_info:
        pass

    @empty_href_wrap
    def get_coach_info(self, href, pager):
        info = self.coach_info(href, pager)
        if not info.href in self.coach_id_cache.keys():
            info.fetch(self.coach_max_id)
            self.coach_id_cache.update({info.href: info.id})
            self.coach_max_id += 1
            self.save(info.output, 'coach_info')
        return info

    @abstractmethod
    def player_info(self, href, pager) -> player_info:
        pass

    @empty_href_wrap
    def get_player_info(self, href, pager):
        info = self.player_info(href, pager)
        if not info.href in self.player_id_cache.keys():
            info.fetch(self.player_max_id)
            self.player_id_cache.update({info.href: info.id})
            self.player_max_id += 1
            self.save(info.output, 'player_info')
        return info

    @abstractmethod
    def team_info(self, href, pager) -> team_info:
        pass

    @empty_href_wrap
    def get_team_info(self, href, pager):
        info = self.team_info(href, pager)
        if not info.href in self.team_id_cache.keys():
            info.fetch(self.team_max_id)
            self.team_id_cache.update({info.href: info.id})
            self.team_max_id += 1
            self.get_links(info, pager)
            self.save(info.output, 'team_info')
        return info

    @abstractmethod
    def season_info(self, href, pager) -> season_info:
        pass

    @empty_href_wrap
    def get_season_info(self, href, pager):
        info = self.season_info(href, pager)
        if not info.href in self.season_id_cache.keys():
            info.fetch()
            self.season_id_cache.update({info.href: info.season})
            self.rankings.update(info.rankings)
            self.get_links(info, pager)
            self.save(info.output, 'season_info')
        return info

    @abstractmethod
    def game_info(self, href, pager) -> game_info:
        pass

    @empty_href_wrap
    def get_game_info(self, href, pager):
        info = self.game_info(href, pager)
        if not info.href in self.game_id_cache.keys():
            info.fetch(self.game_max_id)
            self.game_id_cache.update({info.href: info.id})
            self.game_max_id += 1
            self.get_links(info, pager)
            self.save(info.output, 'game_info')
        return info

    @abstractmethod
    def game_data(self, href, pager) -> game_data:
        pass

    @empty_href_wrap
    def get_game_data(self, href, pager):
        info = self.game_data(href, pager)
        info.fetch()
        self.get_links(info, pager)
        self.save(info.team_data, 'team_data')
        self.save(info.player_data, 'player_data')
        self.save(info.team_data_quarters, 'team_data_quarters')
        self.save(info.player_data_quarters, 'player_data_quarters')
        return info
