# nba.py
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

import re

from . import abstract
from ..debug import debug

_STATS_BASE_URL = "https://stats.nba.com"

_REFEREE_DATA = {}

# season (the year it ends) -> {"/team/<teamId>/<season>": {wins, losses, rank,
# playoff, name}}. Built by season_info._fetch from stats.nba.com standings.
_SEASON_STANDINGS = {}


def _stat(row_dict, key):
    """Coerce a boxscore stat to an int, defaulting None/missing to 0."""
    value = row_dict.get(key)
    return value if value is not None else 0


def _get_boxscore(pager, game_id, range_type=0, start_period=1, end_period=10):
    href = (
        "/stats/boxscoretraditionalv2"
        "?EndPeriod=%d&EndRange=28800&GameID=%s"
        "&RangeType=%d&StartPeriod=%d&StartRange=0"
        % (end_period, game_id, range_type, start_period)
    )
    resp = pager.get(href, base_url=_STATS_BASE_URL)
    if resp:
        return resp
    return {}


def _parse_date(date_str):
    """Parse (year, month) from a 'YYYYMMDD' or ISO 'YYYY-MM-DD...' string."""
    date_str = date_str.strip()
    if not date_str[:4].isdigit():
        return None
    year = int(date_str[:4])
    if len(date_str) >= 6 and date_str[4:6].isdigit():
        month = int(date_str[4:6])
    elif len(date_str) >= 7 and date_str[5:7].isdigit():
        month = int(date_str[5:7])
    else:
        month = 1
    return year, month


def _game_season(game):
    """Best-effort NBA season (the year the season ends) for a game dict.

    The nba.com game page does not expose a season field, so the season is
    derived from the game date. A game played in October, November, or December
    belongs to the season that ends in the following year; games from January
    through September belong to the season ending that same year.
    """
    candidates = (
        game.get("gameCode", "").split("/")[0],  # YYYYMMDD
        game.get("gameEt", ""),                  # YYYY-MM-DD...
        game.get("gameTimeUTC", ""),             # YYYY-MM-DD...
    )
    for candidate in candidates:
        parsed = _parse_date(candidate)
        if not parsed:
            continue
        year, month = parsed
        if year > 1990:
            return year + 1 if month >= 10 else year
    return 1991


class referee_info(abstract.referee_info):
    def __init__(self, href, pager, id_cache):
        self.href = href
        if href in id_cache.keys():
            self._id = id_cache[href]
            self._fetched = True
        else:
            self.soup = {}
            self._name = None
            self._number = None
            self._birthday = None
            self._id = None
            self._fetched = False

    def _fetch(self):
        data = _REFEREE_DATA.get(self.href, {})
        self._name = data.get("name", "")
        number = str(data.get("jerseyNum", "") or "").strip()
        try:
            self._number = int(number) if number else 0
        except ValueError:
            self._number = 0
        self._birthday = ""


class executive_info(abstract.executive_info):
    def _fetch(self):
        pass


class coach_info(abstract.coach_info):
    def _fetch(self):
        pass


class player_info(abstract.player_info):
    @debug.error_wrap('player_info', 'shoots', str, default='R')
    def get_shoots(self):
        info = (
            self.soup.get("props", {})
            .get("pageProps", {})
            .get("player", {})
            .get("info", {})
        )
        hand = info.get("SHOOTING_HAND")
        if not hand:
            raise KeyError("nba.com does not expose shooting-hand data")
        normalized = str(hand).strip().lower()
        if normalized.startswith("r"):
            return "R"
        if normalized.startswith("l"):
            return "L"
        raise KeyError("unrecognized shooting-hand data: %r" % (hand,))

    def _fetch(self):
        self._shoots = self.get_shoots()

        data = self.soup
        info = (
            data.get("props", {})
            .get("pageProps", {})
            .get("player", {})
            .get("info", {})
        )
        if not info:
            return

        self._name = info.get("DISPLAY_FIRST_LAST", "")
        self._birthday = (info.get("BIRTHDATE") or "").replace("T00:00:00", "")
        school = info.get("SCHOOL") or ""
        self._high_school = 1 if "HS" in school.upper() or "HIGH SCHOOL" in school.upper() else 0
        self._college = 0 if self._high_school else 1
        try:
            self._draft_year = int(info.get("DRAFT_YEAR", 0) or 0)
        except ValueError:
            self._draft_year = 0
        try:
            self._draft_position = int(info.get("DRAFT_NUMBER", 0) or 0)
        except ValueError:
            self._draft_position = 0
        self._debut_date = str(info.get("FROM_YEAR", ""))
        self._career_seasons = info.get("SEASON_EXP", 0)


class team_info(abstract.team_info):
    def __init__(self, href, pager, id_cache):
        self.href = href
        if href in id_cache.keys():
            self._id = id_cache[href]
            self._season = None
            self._fetched = True
        else:
            # href is "/team/<teamId>/<season>"; the season qualifies the
            # id_cache key so each franchise gets one team ID per season.
            # nba.com team pages are not season-scoped, so strip the season
            # for the request.
            parts = href.split("/")
            self._season = int(parts[3]) if len(parts) > 3 else None
            base_href = "/".join(parts[:3])
            self.soup = pager.get(base_href)
            self._name = None
            self._abbreviation = None
            self._wins = None
            self._losses = None
            self._location = None
            self._playoff_appearance = None
            self._ranking = None
            self._id = None
            self._executive = None
            self._executive_href = None
            self._coach = None
            self._coach_href = None
            self._fetched = False

    def _fetch(self):
        standings = None
        if self._season is not None:
            standings = _SEASON_STANDINGS.get(self._season, {}).get(self.href)

        data = self.soup
        team = (
            data.get("props", {})
            .get("pageProps", {})
            .get("team", {})
        )
        info = team.get("info", {})

        if standings is not None:
            self._wins = standings["wins"]
            self._losses = standings["losses"]
            self._ranking = standings["rank"]
            self._playoff_appearance = standings["playoff"]
            self._name = standings["name"]
        else:
            self._wins = info.get("W", 0)
            self._losses = info.get("L", 0)
            conf_rank = info.get("CONF_RANK") or 0
            self._playoff_appearance = bool(conf_rank > 0)
            self._ranking = conf_rank or 99
            if self._season is None:
                self._season = int(str(info.get("SEASON_YEAR") or "1990").split("-")[0]) + 1
            self._name = info.get("TEAM_CITY", "") + " " + info.get("TEAM_NAME", "")

        self._location = info.get("TEAM_CITY", "")
        self._abbreviation = info.get("TEAM_ABBREVIATION", "")


class season_info(abstract.season_info):
    def __init__(self, href, pager, id_cache):
        self.href = href
        self.pager = pager
        if href in id_cache.keys():
            self._season = id_cache[href]
            self._fetched = True
        else:
            # The boxscores page is never read by _fetch (the schedule and
            # team records come from stats.nba.com APIs), so skip the request.
            self.soup = {}
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

    def _fetch(self):
        match = re.search(r"[Ss]eason=(\d{4}-\d{2})", self.href)
        season_str = match.group(1) if match else ""
        self._season = int(season_str.split("-")[0]) + 1 if season_str else 1991
        self._games = 0
        self._teams = 0
        self._champion = 0
        self._finals_mvp = 0
        self._mvp = 0
        self._dpoy = 0
        self._mip = 0
        self._sixmoty = 0
        self._roty = 0
        self._rankings = {}
        self._schedule = []

        if not season_str:
            return

        _REFEREE_DATA.clear()

        season_types = ["Regular+Season", "Playoffs", "PlayIn", "IST"]
        game_ids = []
        for season_type in season_types:
            href = (
                "/stats/leaguegamelog"
                "?LeagueID=00&Season=" + season_str +
                "&SeasonType=" + season_type + "&Counter=2500"
                "&PlayerOrTeam=T&Sorter=DATE&Direction=DESC"
            )
            resp = self.pager.get(href, base_url=_STATS_BASE_URL)
            for rs in resp.get("resultSets", []):
                if rs.get("name") != "LeagueGameLog":
                    continue
                headers = rs.get("headers", [])
                for row in rs.get("rowSet", []):
                    row_dict = dict(zip(headers, row))
                    game_id = row_dict.get("GAME_ID", "")
                    if game_id and game_id not in game_ids:
                        game_ids.append(game_id)
        self._schedule = ["/game/" + gid for gid in game_ids]
        self._games = len(self._schedule)

        # Per-season team records: standings give season-accurate W/L/rank and
        # the playoffs game log gives the exact set of teams that made the
        # playoffs. Keyed by the season-qualified team href so team_info can
        # look them up regardless of when in the scrape the team is first seen.
        season_standings = {}
        resp = self.pager.get(
            "/stats/leaguestandings"
            "?LeagueID=00&Season=" + season_str + "&SeasonType=Regular+Season"
            "&Conference=&Division=&Location=&Outcome=&PORound=&PlayerPosition="
            "&Scope=S&StatCategory=PTS",
            base_url=_STATS_BASE_URL,
        )
        for rs in resp.get("resultSets", []):
            if rs.get("name") != "Standings":
                continue
            headers = rs.get("headers", [])
            rows = [dict(zip(headers, row)) for row in rs.get("rowSet", [])]
            rows.sort(key=lambda d: (-d["WINS"], d["LOSSES"]))
            for rank, row in enumerate(rows, 1):
                team_href = "/team/%d/%d" % (row["TeamID"], self._season)
                season_standings[team_href] = {
                    "wins": row["WINS"],
                    "losses": row["LOSSES"],
                    "rank": rank,
                    "playoff": False,
                    "name": row["TeamCity"] + " " + row["TeamName"],
                }

        resp = self.pager.get(
            "/stats/leaguegamefinder"
            "?LeagueID=00&Season=" + season_str + "&SeasonType=Playoffs"
            "&PlayerOrTeam=T",
            base_url=_STATS_BASE_URL,
        )
        playoff_ids = set()
        for rs in resp.get("resultSets", []):
            headers = rs.get("headers", [])
            for row in rs.get("rowSet", []):
                row_dict = dict(zip(headers, row))
                team_id = row_dict.get("TEAM_ID")
                if team_id is not None:
                    playoff_ids.add(team_id)
        for team_href in season_standings:
            if int(team_href.split("/")[2]) in playoff_ids:
                season_standings[team_href]["playoff"] = True

        _SEASON_STANDINGS[self._season] = season_standings


class game_info(abstract.game_info):
    def _fetch(self):
        data = self.soup
        game = (
            data.get("props", {})
            .get("pageProps", {})
            .get("game", {})
        )
        if not game:
            return

        home = game.get("homeTeam", {})
        away = game.get("awayTeam", {})
        season = _game_season(game)
        self._home_team_name = home.get("teamName", "")
        self._home_team_href = "/team/" + str(home.get("teamId", "")) + "/" + str(season)
        self._away_team_name = away.get("teamName", "")
        self._away_team_href = "/team/" + str(away.get("teamId", "")) + "/" + str(season)

        self._attendance = game.get("attendance", 0)
        arena = game.get("arena", {})
        self._location = arena.get("arenaName", "")
        if arena.get("arenaCity"):
            self._location += ", " + arena.get("arenaCity")
        if arena.get("arenaState"):
            self._location += ", " + arena.get("arenaState")

        dur_min = game.get("duration", 0)
        try:
            parts = str(dur_min).split(":")
            self._duration = int(parts[0]) * 60 + int(parts[1])
        except (ValueError, IndexError):
            self._duration = 0

        officials = game.get("officials", [])
        self._referee_hrefs = []
        for official in officials:
            referee_id = official.get("personId")
            if not referee_id:
                continue
            href = "/referee/" + str(referee_id)
            self._referee_hrefs.append(href)
            _REFEREE_DATA[href] = official

        game_id = str(game.get("gameId", ""))
        if game_id.startswith("004"):
            self._type = "playoffs"
            self._playoffs = True
            self._in_season_tournament = False
            self._play_in = False
        elif game_id.startswith("005"):
            self._type = "play-in"
            self._playoffs = False
            self._in_season_tournament = False
            self._play_in = True
        elif game_id.startswith("006"):
            self._type = "in-season tournament"
            self._playoffs = False
            self._in_season_tournament = True
            self._play_in = False
        else:
            subtype = game.get("gameSubtype", "")
            label = game.get("gameLabel", "")
            text = (subtype + " " + label).lower()
            if "in-season" in text or "cup" in text:
                self._type = "in-season tournament"
                self._playoffs = False
                self._in_season_tournament = True
                self._play_in = False
            elif "play-in" in text or "playin" in text:
                self._type = "play-in"
                self._playoffs = False
                self._in_season_tournament = False
                self._play_in = True
            elif "playoff" in text:
                self._type = "playoffs"
                self._playoffs = True
                self._in_season_tournament = False
                self._play_in = False
            else:
                self._type = "regular"
                self._playoffs = False
                self._in_season_tournament = False
                self._play_in = False

        game_code = game.get("gameCode", "")
        parts = game_code.split("/")
        date_str = parts[0] if parts else ""
        if len(date_str) >= 8:
            self._date = date_str[:4] + "-" + date_str[4:6] + "-" + date_str[6:8]
        else:
            self._date = ""

        self._season = season

    @property
    def home_team_href(self):
        return self._home_team_href

    @property
    def away_team_href(self):
        return self._away_team_href


class game_data(abstract.game_data):
    @staticmethod
    def initialize_table() -> dict:
        return {
            "Quarter": [],
            "Seconds": [],
            "Threes": [],
            "Three_Attempts": [],
            "Field_Goals": [],
            "Field_Goal_Attempts": [],
            "Freethrows": [],
            "Freethrow_Attempts": [],
            "Offensive_Rebounds": [],
            "Defensive_Rebounds": [],
            "Assists": [],
            "Steals": [],
            "Blocks": [],
            "Turnovers": [],
            "Fouls": [],
            "Points": [],
            "PM": [],
            "Win": [],
            "Home": [],
            "Player_ID": [],
            "Game_ID": [],
            "Season": [],
            "Team_ID": [],
            "Opponent_ID": [],
        }

    def _add_player_rows(self, target, rows, headers, home_team, away_team,
                         home_href, away_href, home_win, season, period):
        for row in rows:
            row_dict = dict(zip(headers, row))
            person_id = row_dict.get("PLAYER_ID", "")
            if not person_id:
                continue
            player_href = "/player/" + str(person_id)
            team_id = home_href if str(row_dict.get("TEAM_ID")) == str(home_team.get("teamId")) else away_href
            opp_href = away_href if team_id == home_href else home_href

            minutes = row_dict.get("MIN")
            if not minutes:
                continue
            try:
                parts = minutes.split(":")
                secs = int(parts[0]) * 60 + int(parts[1])
            except (ValueError, IndexError):
                secs = 0

            target["Quarter"].append(period)
            target["Seconds"].append(secs)
            target["Threes"].append(_stat(row_dict, "FG3M"))
            target["Three_Attempts"].append(_stat(row_dict, "FG3A"))
            target["Field_Goals"].append(_stat(row_dict, "FGM"))
            target["Field_Goal_Attempts"].append(_stat(row_dict, "FGA"))
            target["Freethrows"].append(_stat(row_dict, "FTM"))
            target["Freethrow_Attempts"].append(_stat(row_dict, "FTA"))
            target["Offensive_Rebounds"].append(_stat(row_dict, "OREB"))
            target["Defensive_Rebounds"].append(_stat(row_dict, "DREB"))
            target["Assists"].append(_stat(row_dict, "AST"))
            target["Steals"].append(_stat(row_dict, "STL"))
            target["Blocks"].append(_stat(row_dict, "BLK"))
            target["Turnovers"].append(_stat(row_dict, "TOV"))
            target["Fouls"].append(_stat(row_dict, "PF"))
            target["Points"].append(_stat(row_dict, "PTS"))
            target["PM"].append(_stat(row_dict, "PLUS_MINUS"))
            target["Win"].append(home_win if team_id == home_href else not home_win)
            target["Home"].append(team_id == home_href)
            target["Player_ID"].append(player_href)
            target["Game_ID"].append(self.href)
            target["Season"].append(season)
            target["Team_ID"].append(team_id)
            target["Opponent_ID"].append(opp_href)

    def _add_team_rows(self, target, rows, headers, home_team, away_team,
                       home_href, away_href, home_win, season, period):
        for row in rows:
            row_dict = dict(zip(headers, row))
            team_id = (
                home_href
                if str(row_dict.get("TEAM_ID")) == str(home_team.get("teamId"))
                else away_href
            )
            opp_href = away_href if team_id == home_href else home_href

            minutes = row_dict.get("MIN") or "0:00"
            try:
                parts = minutes.split(":")
                secs = int(parts[0]) * 60 + int(parts[1])
            except (ValueError, IndexError):
                secs = 0

            target["Quarter"].append(period)
            target["Seconds"].append(secs)
            target["Threes"].append(_stat(row_dict, "FG3M"))
            target["Three_Attempts"].append(_stat(row_dict, "FG3A"))
            target["Field_Goals"].append(_stat(row_dict, "FGM"))
            target["Field_Goal_Attempts"].append(_stat(row_dict, "FGA"))
            target["Freethrows"].append(_stat(row_dict, "FTM"))
            target["Freethrow_Attempts"].append(_stat(row_dict, "FTA"))
            target["Offensive_Rebounds"].append(_stat(row_dict, "OREB"))
            target["Defensive_Rebounds"].append(_stat(row_dict, "DREB"))
            target["Assists"].append(_stat(row_dict, "AST"))
            target["Steals"].append(_stat(row_dict, "STL"))
            target["Blocks"].append(_stat(row_dict, "BLK"))
            target["Turnovers"].append(_stat(row_dict, "TOV"))
            target["Fouls"].append(_stat(row_dict, "PF"))
            target["Points"].append(_stat(row_dict, "PTS"))
            target["Win"].append(home_win if team_id == home_href else not home_win)
            target["Home"].append(team_id == home_href)
            target["Team_ID"].append(team_id)
            target["Opponent_ID"].append(opp_href)
            target["Game_ID"].append(self.href)
            target["Season"].append(season)

    def _fetch(self):
        game = self.soup.get("props", {}).get("pageProps", {}).get("game", {})
        if not game:
            return

        game_id = game.get("gameId", "")
        home_team = game.get("homeTeam", {})
        away_team = game.get("awayTeam", {})
        season = _game_season(game)
        home_href = "/team/" + str(home_team.get("teamId", "")) + "/" + str(season)
        away_href = "/team/" + str(away_team.get("teamId", "")) + "/" + str(season)
        home_win = home_team.get("score", 0) > away_team.get("score", 0)

        boxscore = _get_boxscore(self.pager, game_id)
        result_sets = boxscore.get("resultSets", [])

        player_data = self.initialize_table()
        team_data = self.initialize_table()
        player_data_quarters = self.initialize_table()
        team_data_quarters = self.initialize_table()

        for rs in result_sets:
            name = rs.get("name", "")
            headers = rs.get("headers", [])
            rows = rs.get("rowSet", [])

            if name == "PlayerStats":
                self._add_player_rows(player_data, rows, headers, home_team,
                                      away_team, home_href, away_href,
                                      home_win, season, "whole")
            elif name == "TeamStats":
                self._add_team_rows(team_data, rows, headers, home_team,
                                    away_team, home_href, away_href,
                                    home_win, season, "whole")

        # Per-quarter data: one boxscore request per period played (RangeType=1).
        # A failed period is logged and skipped so one bad request can't silently
        # truncate the remaining quarters.
        num_periods = len(home_team.get("periods", []))
        if num_periods == 0:
            num_periods = 4
        missing_periods = []
        for period in range(1, min(num_periods, 8) + 1):
            period_boxscore = _get_boxscore(
                self.pager, game_id, range_type=1,
                start_period=period, end_period=period,
            )
            period_sets = period_boxscore.get("resultSets", [])
            if not period_sets:
                missing_periods.append(period)
                continue
            for rs in period_sets:
                name = rs.get("name", "")
                headers = rs.get("headers", [])
                rows = rs.get("rowSet", [])
                if name == "PlayerStats" and rows:
                    self._add_player_rows(player_data_quarters, rows, headers,
                                          home_team, away_team, home_href,
                                          away_href, home_win, season, period)
                elif name == "TeamStats" and rows:
                    self._add_team_rows(team_data_quarters, rows, headers,
                                        home_team, away_team, home_href,
                                        away_href, home_win, season, period)
        if missing_periods:
            debug.debug("game_data",
                        "missing per-quarter data for periods %s of game %s"
                        % (missing_periods, self.href))

        # Whole-game tables omit the Quarter column; per-quarter tables keep it
        del player_data["Quarter"]
        del team_data["Quarter"]
        # team_games / team_quarters have no PM or Player_ID columns; drop them
        # so the column names match the table and zip doesn't truncate the rows
        team_data.pop("PM", None)
        team_data.pop("Player_ID", None)
        team_data_quarters.pop("PM", None)
        team_data_quarters.pop("Player_ID", None)

        self._player_data = player_data
        self._player_data_quarters = player_data_quarters
        self._team_data = team_data
        self._team_data_quarters = team_data_quarters
        self._home_win = home_win


class NBAEngine(abstract.engine):
    def __init__(self, pager, database):
        super().__init__(pager, database)
        self._source = "nba"

    def get_season_info(self, href):
        info = self.season_info(href)
        if href not in self.season_id_cache.keys():
            return super().get_season_info(href)
        # A season already in the id_cache skips _fetch in the base class, so
        # _SEASON_STANDINGS would never be built in this process and any team
        # scraped now would fall back to current-snapshot data. Rebuild the
        # standings so resumed/incremental scrapes get season-accurate rows.
        info._fetch()
        return info

    def get_id_cache(self):
        cols = ["nba", "value"]
        locations = [
            ("referee_info", self.referee_id_cache),
            ("executive_info", self.executive_id_cache),
            ("coach_info", self.coach_id_cache),
            ("player_info", self.player_id_cache),
            ("team_info", self.team_id_cache),
            ("season_info", self.season_id_cache),
            ("game_info", self.game_id_cache),
            ("game_data", self.game_data_cache),
            ("rankings", self.rankings),
        ]
        try:
            con = self.database.give_connection()
            cur = con.cursor()
            for location, cache in locations:
                query = f"SELECT {','.join(cols)} FROM id_cache WHERE type = '{location}'"
                tmp = cur.execute(query)
                from_cache = {href: value for href, value in cur.fetchall()}
                cache.update(from_cache)
            cur.close()
            con.close()
        except Exception:
            pass

        self.referee_max_id = max([0] + list(self.referee_id_cache.values()))
        self.executive_max_id = max([0] + list(self.executive_id_cache.values()))
        self.coach_max_id = max([0] + list(self.coach_id_cache.values()))
        self.player_max_id = max([0] + list(self.player_id_cache.values()))
        self.team_max_id = max([0] + list(self.team_id_cache.values()))
        self.game_max_id = max([0] + list(self.game_id_cache.values()))

    def referee_info(self, href):
        return referee_info(href, self.pager, self.referee_id_cache)

    def executive_info(self, href):
        return executive_info(href, self.pager, self.executive_id_cache)

    def coach_info(self, href):
        return coach_info(href, self.pager, self.coach_id_cache)

    def player_info(self, href):
        return player_info(href, self.pager, self.player_id_cache)

    def team_info(self, href):
        return team_info(href, self.pager, self.team_id_cache)

    def season_info(self, href):
        return season_info(href, self.pager, self.season_id_cache)

    def game_info(self, href):
        return game_info(href, self.pager, self.game_id_cache)

    def game_data(self, href):
        return game_data(href, self.pager, self.game_data_cache)