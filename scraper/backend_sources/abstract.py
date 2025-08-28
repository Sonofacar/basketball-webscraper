# backend_sources/abstract.py
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

from abc import abstractmethod
from ..debug import debug
from functools import wraps

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
        self._output = {'Name': [self.name if self.name is not None else ''],
                        'Number': [self.number if self.number is not None else 0],
                        'Birthday': [self.birthday if self.birthday is not None else ''],
                        'Referee_ID': [self.id if self.id is not None else 0]}

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
        self._output = {'Name': [self.name if self.name is not None else ''],
                        'Birthday': [self.birthday if self.birthday is not None else ''],
                        'Executive_ID': [self.id if self.id is not None else 0]}

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
        self._output = {'Name': [self.name if self.name is not None else ''],
                        'Birthday': [self.birthday if self.birthday is not None else ''],
                        'Wins': [self.wins if self.wins is not None else 0],
                        'Losses': [self.losses if self.losses is not None else 0],
                        'Coach_ID': [self.id if self.id is not None else 0]}

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
        HS = self.high_school
        DP = self.draft_position
        DT = self.draft_team
        DY = self.draft_year
        DD = self.debut_date
        CS = self.career_seasons
        self._output = {'Name': [self.name if self.name is not None else ''],
                        'Shoots': [self.shoots if self.shoots is not None else ''],
                        'Birthday': [self.birthday if self.birthday is not None else ''],
                        'High_School': [HS if HS is not None else 0],
                        'College': [self.college if self.college is not None else 0],
                        'Draft_Position': [DP if DP is not None else 0],
                        'Draft_Team': [DT if DT is not None else ''],
                        'Draft_Year': [DY if DY is not None else 0],
                        'Debut_Date': [DD if DD is not None else ''],
                        'Player_ID': [self.id if self.id is not None else 0]}

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
        abbrev = self.abbreviation
        PA = self.playoff_appearance
        LR = self.ranking
        EXEC = self.executive
        self._output = {'Name': [self.name if self.name is not None else ''],
                        'Abbreviation': [abbrev if abbrev is not None else ''],
                        'Wins': [self.wins if self.wins is not None else 0],
                        'Losses': [self.losses if self.losses is not None else 0],
                        'Location': [self.location if self.location is not None else ''],
                        'Playoff_Appearance': [PA if PA is not None else 0],
                        'League_Ranking': [LR if LR is not None else 99],
                        'Team_ID': [self.id if self.id is not None else 0],
                        'Season': [self.season if self.season is not None else 1990],
                        'Executive_ID': [EXEC if EXEC is not None else 0],
                        'Coach_ID': [self.coach if self.coach is not None else 0]}

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
        fMVP = self.finals_mvp
        self._output = {'Season': [self.season if self.season is not None else 1990],
                        'Games': [self.games if self.games is not None else 0],
                        'Teams': [self.teams if self.teams is not None else 0],
                        'Champion': [self.champion if self.champion is not None else 0],
                        'Finals_MVP': [fMVP if fMVP is not None else 0],
                        'MVP': [self.mvp if self.mvp is not None else 0],
                        'DPOY': [self.dpoy if self.dpoy is not None else 0],
                        'MIP': [self.mip if self.mip is not None else 0],
                        'SixMOTY': [self.sixmoty if self.sixmoty is not None else 0],
                        'ROTY': [self.roty if self.roty is not None else 0]}

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
        HTN = self.home_team_name
        ATN = self.away_team_name
        attend = self.attendance
        HTID = self.home_team_id
        ATID = self.away_team_id
        IST = self.in_season_tournament
        ref1 = self.referee_ids[0]
        ref2 = self.referee_ids[1]
        ref3 = self.referee_ids[2]
        self._output = {'Home_Team_Name': [HTN if HTN is not None else ''],
                        'Away_Team_Name': [ATN if ATN is not None else ''],
                        'Date': [self.date if self.date is not None else ''],
                        'Location': [self.location if self.location is not None else ''],
                        'Duration': [self.duration if self.duration is not None else 0],
                        'Attendance': [attend if attend is not None else 0],
                        'Game_ID': [self.id if self.id is not None else 0],
                        'Home_Team_ID': [HTID if HTID is not None else 0],
                        'Away_Team_ID': [ATID if ATID is not None else 0],
                        'Season': [self.season if self.season is not None else 1990],
                        'Playoffs': [self.playoffs if self.playoffs is not None else 0],
                        'In_Season_Tournament': [IST if IST is not None else 0],
                        'Play_In': [self.play_in if self.play_in is not None else 0],
                        'Referee_ID1': [ref1 if ref1 is not None else 0],
                        'Referee_ID2': [ref2 if ref2 is not None else 0],
                        'Referee_ID3': [ref3 if ref3 is not None else 0]}

    def fetch(self, prev = 0):
        if self._fetched:
            return # Already fetched
        self.gen_id(prev)
        self._fetch()
        self._fetched = True
        self.refresh_output()

class game_data(debug):
    def __init__(self, href, pager, id_cache):
        self.href = href
        if href in id_cache.keys():
            self._fetched = True
        else: 
            self.soup = pager.get(href)
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
    def __init__(self, pager, database):
        self.pager = pager
        self.database = database
        self._source = ""

    referee_max_id = 0
    executive_max_id = 0
    coach_max_id = 0
    player_max_id = 0
    team_max_id = 0
    game_max_id = 0
    referee_id_cache = {}
    executive_id_cache = {}
    coach_id_cache = {}
    player_id_cache = {}
    team_id_cache = {}
    season_id_cache = {}
    game_id_cache = {}
    game_data_cache = {}
    rankings = {}

    @abstractmethod
    def get_id_cache(self):
        pass

    @property
    def source(self):
        return self._source

    def update_id_cache(self, href, ID, cache, location):
        id_data = {self.source: [href],
                   "value": [ID],
                   "type": [location]}
        self.database.save_data(id_data, "id_cache")
        cache.update({href: ID})

    @staticmethod
    def safe_set_id(obj):
        if obj == None:
            return None
        else:
            return obj.id

    def link_game_data(self, table):
        tmp = [self.get_game_info(x) for x in table['Game_ID']]
        ids = [self.safe_set_id(x) for x in tmp]
        table.update({'Game_ID': ids})

        tmp = [self.get_team_info(x) for x in table['Team_ID']]
        ids = [self.safe_set_id(x) for x in tmp]
        table.update({'Team_ID': ids})

        tmp = [self.get_team_info(x) for x in table['Opponent_ID']]
        ids = [self.safe_set_id(x) for x in tmp]
        table.update({'Opponent_ID': ids})

        if 'Player_ID' in table.keys():
            tmp = [self.get_player_info(x) for x in table['Player_ID']]
            ids = [self.safe_set_id(x) for x in tmp]
            table.update({'Player_ID': ids})

    def get_links(self, obj):
        if issubclass(obj.__class__, team_info):
            executive = self.get_executive_info(obj.executive_href)
            obj.executive = self.safe_set_id(executive)
            coach = self.get_coach_info(obj.coach_href)
            obj.coach = self.safe_set_id(coach)
            rank = self.rankings.get(obj.href, None)
            obj.refresh_output()

        elif issubclass(obj.__class__, season_info):
            champion = self.get_team_info(obj.champion_href)
            obj.champion = self.safe_set_id(champion)
            finals_mvp = self.get_player_info(obj.finals_mvp_href)
            obj.finals_mvp = self.safe_set_id(finals_mvp)
            mvp = self.get_player_info(obj.mvp_href)
            obj.mvp = self.safe_set_id(mvp)
            dpoy = self.get_player_info(obj.dpoy_href)
            obj.dpoy = self.safe_set_id(dpoy)
            mip = self.get_player_info(obj.mip_href)
            obj.mip = self.safe_set_id(mip)
            sixmoty = self.get_player_info(obj.sixmoty_href)
            obj.sixmoty = self.safe_set_id(sixmoty)
            roty = self.get_player_info(obj.roty_href)
            obj.roty = self.safe_set_id(roty)
            obj.refresh_output()

            games = [self.get_game_data(x) for x in obj.schedule]

        elif issubclass(obj.__class__, game_info):
            home = self.get_team_info(obj.home_team_href)
            obj.home_team_id = self.safe_set_id(home)
            away = self.get_team_info(obj.away_team_href)
            obj.away_team_id = self.safe_set_id(away)
            refs = [self.get_referee_info(x) for x in obj.referee_hrefs]
            ref_ids = [self.safe_set_id(x) for x in refs]
            obj.referee_ids = ref_ids
            obj.refresh_output()

        elif issubclass(obj.__class__, game_data):
            self.link_game_data(obj.team_data)
            self.link_game_data(obj.player_data)
            self.link_game_data(obj.team_data_quarters)
            self.link_game_data(obj.player_data_quarters)

    @abstractmethod
    def referee_info(self, href) -> referee_info:
        pass

    @empty_href_wrap
    def get_referee_info(self, href):
        info = self.referee_info(href)
        if not href in self.referee_id_cache.keys():
            info.fetch(self.referee_max_id)
            self.referee_max_id += 1
            self.update_id_cache(href,
                                 info.id,
                                 self.referee_id_cache,
                                 "referee_info")
            self.database.save_data(info.output, 'referee_info')
        return info

    @abstractmethod
    def executive_info(self, href) -> executive_info:
        pass

    @empty_href_wrap
    def get_executive_info(self, href):
        info = self.executive_info(href)
        if not href in self.executive_id_cache.keys():
            info.fetch(self.executive_max_id)
            self.executive_max_id += 1
            self.update_id_cache(href,
                                 info.id,
                                 self.executive_id_cache,
                                 "executive_info")
            self.database.save_data(info.output, 'executive_info')
        return info

    @abstractmethod
    def coach_info(self, href) -> coach_info:
        pass

    @empty_href_wrap
    def get_coach_info(self, href):
        info = self.coach_info(href)
        if not href in self.coach_id_cache.keys():
            info.fetch(self.coach_max_id)
            self.coach_max_id += 1
            self.update_id_cache(href,
                                 info.id,
                                 self.coach_id_cache,
                                 "coach_info")
            self.database.save_data(info.output, 'coach_info')
        return info

    @abstractmethod
    def player_info(self, href) -> player_info:
        pass

    @empty_href_wrap
    def get_player_info(self, href):
        info = self.player_info(href)
        if not href in self.player_id_cache.keys():
            info.fetch(self.player_max_id)
            self.player_max_id += 1
            self.update_id_cache(href,
                                 info.id,
                                 self.player_id_cache,
                                 "player_info")
            self.database.save_data(info.output, 'player_info')
        return info

    @abstractmethod
    def team_info(self, href) -> team_info:
        pass

    @empty_href_wrap
    def get_team_info(self, href):
        info = self.team_info(href)
        if not href in self.team_id_cache.keys():
            info.fetch(self.team_max_id)
            self.team_max_id += 1
            self.get_links(info)
            self.update_id_cache(href,
                                 info.id,
                                 self.team_id_cache,
                                 "team_info")
            self.database.save_data(info.output, 'team_info')
        return info

    @abstractmethod
    def season_info(self, href) -> season_info:
        pass

    @empty_href_wrap
    def get_season_info(self, href):
        info = self.season_info(href)
        if not href in self.season_id_cache.keys():
            info.fetch()
            self.rankings.update(info.rankings)
            for key, value in info.rankings.items():
                self.update_id_cache(key, value, self.rankings, "rakings")
            self.get_links(info)
            self.update_id_cache(href,
                                 info.season,
                                 self.season_id_cache,
                                 "season_info")
            self.database.save_data(info.output, 'season_info')
        return info

    @abstractmethod
    def game_info(self, href) -> game_info:
        pass

    @empty_href_wrap
    def get_game_info(self, href):
        info = self.game_info(href)
        if not href in self.game_id_cache.keys():
            info.fetch(self.game_max_id)
            self.game_max_id += 1
            self.get_links(info)
            self.update_id_cache(href,
                                 info.id,
                                 self.game_id_cache,
                                 "game_info")
            self.database.save_data(info.output, 'game_info')
        return info

    @abstractmethod
    def game_data(self, href) -> game_data:
        pass

    @empty_href_wrap
    def get_game_data(self, href):
        info = self.game_data(href)
        if self.game_data_cache.get(href, 0) != 1:
            info.fetch()
            self.get_links(info)
            self.database.save_data(info.team_data, 'team_games')
            self.database.save_data(info.player_data, 'player_games')
            self.database.save_data(info.team_data_quarters, 'team_quarters')
            self.database.save_data(info.player_data_quarters, 'player_quarters')
            self.update_id_cache(href,
                                 1,
                                 self.game_data_cache,
                                 "game_data")
        return info
