# espn.py
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
from ..debug import assume, get_logger

log = get_logger(__name__)

# ESPN splits its data across three hosts. The source passes base_url= for
# whichever one it needs, since the pager's own base_url only covers one.
_CORE_URL = "https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba"
_SITE_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
_STANDINGS_URL = "https://site.api.espn.com/apis/v2/sports/basketball/nba"

# core-api enumerates a season's games by season type. Neither the in-season
# tournament nor the All-Star game has a type of its own: both sit inside the
# regular season bucket. Each such game is identified by its summary header
# gameNote instead ("NBA Cup ..." for the tournament, "NBA All-Star ..." for
# the All-Star games, which are not scraped at all).
_TYPE_REGULAR = 2
_TYPE_PLAYOFFS = 3
_TYPE_PLAY_IN = 5
_SEASON_TYPES = (_TYPE_REGULAR, _TYPE_PLAYOFFS, _TYPE_PLAY_IN)

_PAGE_SIZE = 1000
_MAX_PAGES = 20

# 12 minutes per period. ESPN gives team totals as bare counts with no minutes
# field, so whole-team playing time is derived from the number of periods
# actually played. This matches the basketball-reference convention.
_PERIOD_SECONDS = 720

# The eight seeds in each conference are the playoff field. ESPN's standings
# order is not sorted by wins, so seed is the only reliable qualifier.
_PLAYOFF_SEED_MAX = 8

_REFEREE_DATA = {}

# event id -> core-api season type. Built by season_info._fetch; because the
# schedule is enumerated type by type, every game is classified for free.
_EVENT_TYPE = {}

# season (the year it ends) -> {"/espn/team/<teamId>/<season>": {wins, losses,
# rank, playoff, name}}. Built by season_info._fetch from the standings.
_SEASON_STANDINGS = {}

# ESPN team id -> display name, for draft-team resolution and player teams.
_TEAM_NAMES = {}

# core-api award ids. These are stable across seasons, but each record's name
# is checked against its key when it is read, so a renumbering surfaces as a
# log line instead of silently attaching the wrong trophy to a player. Only the
# seven awards season_info has columns for are listed; core-api publishes
# twenty (All-NBA teams, NBA Cup MVP, and so on), but there is nowhere to put
# them.
_AWARD_IDS = {
    "MVP": 33,
    "Rookie of the Year": 35,
    "Most Improved Player": 36,
    "Defensive Player of the Year": 39,
    "Sixth Man of the Year": 40,
    "Finals MVP": 43,
}

# season (the year it ends) -> {award name: player href}, plus "Champion" for
# the team the Finals MVP played for. Built by season_info._fetch.
_SEASON_AWARDS = {}

# season -> {ESPN team id: "/espn/coach/<personId>"}. Built by
# season_info._fetch from core-api's league-wide season coach list. Unlike team
# and player hrefs, coach hrefs are not season-qualified: the coaches table has
# no Season column, so a coach is one row for their whole career.
_SEASON_COACHES = {}


def _int(value, default=0):
    """Coerce an ESPN stat string to an int, defaulting unparseable values.

    A missing or empty value is an ordinary absent cell and stays silent. A
    string that cannot be parsed means ESPN changed the data shape, and every
    number derived from that cell would silently be wrong, so it is reported.
    """
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        if value is None or str(value).strip() == "":
            return default
        assume("espn stats", "int", default,
               "could not parse %r as an integer" % (value,),
               log=log)
        return default


def _made_attempted(value):
    """Parse an ESPN '38-98' made-attempted pair into (made, attempted)."""
    text = str(value or "").strip()
    if "-" not in text:
        return _int(text), 0
    made, _, attempted = text.partition("-")
    return _int(made), _int(attempted)


def _season_from_date(date_str):
    """Derive the season (the year it ends) from an ESPN ISO date string.

    A game played from July through December belongs to the season that ends
    the following year; January through June belongs to the season ending that
    same year. That puts the regular season, playoffs, and in-season tournament
    all in the right season. Only used as a fallback: the summary header
    normally states the season outright.
    """
    date_str = str(date_str or "").strip()
    if len(date_str) < 4 or not date_str[:4].isdigit():
        return None
    year = int(date_str[:4])
    if len(date_str) >= 7 and date_str[5:7].isdigit():
        month = int(date_str[5:7])
    else:
        month = 1
    return year + 1 if month >= 7 else year


def _summary_season(soup):
    """Season (the year it ends) and season type for a summary payload.

    The summary header states both outright, which is authoritative and
    available even when a single game is scraped outside a season crawl. The
    game date is only consulted if the header is missing a year.
    """
    header = soup.get("header", {}) or {}
    competition = _competition(soup)
    season = header.get("season", {}) or {}
    year = season.get("year")
    if not year or not str(year).isdigit():
        year = _season_from_date(competition.get("date"))
    return year, season.get("type"), competition


def _game_note(soup):
    """The summary header's gameNote label, or "" for an ordinary game.

    ESPN labels the games its season types cannot express: "NBA Cup - Group
    Play"/"NBA Cup - Quarterfinals"/"NBA Cup - Semifinals"/"NBA Cup
    Championship" for the in-season tournament, "NBA All-Star ..." for the
    All-Star games, and one-off series names ("NBA Paris Games 2025", "NBA
    Mexico City Game 2024") for games that are otherwise ordinary regular
    season games.
    """
    header = soup.get("header", {}) or {}
    return header.get("gameNote") or ""


def _skip_reason(note):
    """Why this event must not be scraped, or None to scrape it.

    Deliberately fail-open: only a positive match on ESPN's own label
    excludes an event, so a reworded gameNote degrades to the old behavior
    (the game is scraped as a regular game) instead of silently dropping
    real games.
    """
    if "NBA All-Star" in note:
        return "All-Star game"
    return None


def _team_href(team_id, season):
    return "/espn/team/%s/%s" % (team_id, season)


def _player_href(athlete_id):
    """Build the ESPN player href. Deliberately season-less.

    player_info has no Season column, so a player is one row for a career and
    this href is pure identity: the id_cache keys off it, and a season in the
    key would mint a fresh Player_ID for the same person every season, which
    player_games.Player_ID then FKs to and silently breaks cross-season
    aggregation. Only team hrefs are season-qualified, because team_info does
    carry a Season column.
    """
    return "/espn/athlete/%s" % athlete_id


def _slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", str(name or "").lower()).strip("-")


def _href_parts(href):
    """Split an ESPN href into its non-empty path segments."""
    return [part for part in str(href or "").split("/") if part]


def _core_path(ref):
    """Turn a core-api "$ref" URL into a path usable with _CORE_URL.

    core-api hands back absolute URLs like
    "http://.../leagues/nba/coaches/1/record/0?lang=en", while pager.get takes
    a path relative to a base_url. Returns "" if the ref is not a core-api URL.
    """
    text = str(ref or "").strip()
    marker = "/leagues/nba"
    index = text.find(marker)
    if index < 0:
        return ""
    return text[index + len(marker):]


def _record_wl(value):
    """Parse a "286-129-0" record string into (wins, losses)."""
    parts = str(value or "").strip().split("-")
    wins = _int(parts[0]) if parts and parts[0].strip() else 0
    losses = _int(parts[1]) if len(parts) > 1 else 0
    return wins, losses


def _competition(soup):
    """Return the single header competition of a summary, or {}."""
    competitions = soup.get("header", {}).get("competitions", [])
    return competitions[0] if competitions else {}


def _sides(competition):
    """Split a competition's competitors into (home, away) competitor dicts."""
    home = away = None
    for competitor in competition.get("competitors", []) or []:
        side = competitor.get("homeAway")
        if side == "home":
            home = competitor
        elif side == "away":
            away = competitor
    return home, away


def _team_id(block):
    """ESPN team id from any object that nests a "team" dict, whether that is a
    header competitor or a boxscore team/player entry."""
    return str((block or {}).get("team", {}).get("id", "") or "")


def _team_name(pager, team_id):
    """Resolve an ESPN team id to a display name, caching each lookup."""
    team_id = str(team_id or "")
    if not team_id:
        return ""
    if team_id in _TEAM_NAMES:
        return _TEAM_NAMES[team_id]
    data = pager.get("/teams/" + team_id, base_url=_CORE_URL) or {}
    name = data.get("displayName") or ""
    if not name:
        location = data.get("location", "")
        name = (location + " " + data.get("name", "")).strip()
    _TEAM_NAMES[team_id] = name
    return name


class referee_info(abstract.referee_info):
    """ESPN has no referee pages and no referee ids, only the officials' names
    on the game page, so this is filled from the module-level table that
    game_info populates. No request is made."""

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
        self._name = data.get("name") or self.href.rsplit("/", 1)[-1].replace("-", " ")
        self._name = str(self._name).strip()
        self._number = _int(data.get("number", 0))
        self._birthday = ""


class executive_info(abstract.executive_info):
    """ESPN publishes no executive profiles, so every field is a default."""

    def _fetch(self):
        # Every column in the executives table is a type default; say so once
        # instead of writing a row of zeros with no trace.
        assume("executive_info", "Executive_ID", 0,
               "ESPN publishes no executive profiles, so every column stays "
               "at its type default",
               context=self.href, log=log)


class coach_info(abstract.coach_info):
    """ESPN's coach resource carries a name and career records.

    href is "/espn/coach/<personId>", deliberately not season-qualified: the
    coaches table has no Season column, so a coach is a single career row.
    Wins and Losses come from the profile's first careerRecords entry (the
    "Total" record, a "286-129-0" displayValue). ESPN has no date of birth for
    coaches, only a birth place, so Birthday is left empty.
    """

    def __init__(self, href, pager, id_cache):
        self.href = href
        self.pager = pager
        if href in id_cache.keys():
            self._id = id_cache[href]
            self._fetched = True
        else:
            # The abstract __init__ would request href against the pager's
            # site-api base URL, where no coach resource exists.
            parts = _href_parts(href)
            person_id = parts[2] if len(parts) > 2 else ""
            self.soup = {}
            if person_id.isdigit():
                self.soup = pager.get(
                    "/coaches/" + person_id, base_url=_CORE_URL) or {}
            self._name = None
            self._birthday = None
            self._wins = None
            self._losses = None
            self._teams = None
            self._id = None
            self._fetched = False

    def _fetch(self):
        data = self.soup
        name = " ".join(
            part for part in (data.get("firstName"), data.get("lastName"))
            if part
        )
        self._name = name or data.get("displayName") or ""
        # ESPN has no date of birth for coaches, only a birth place, so the
        # Birthday column is a silent-but-reported assumption.
        self._birthday = ""
        assume("coach_info", "birthday", "",
               "ESPN publishes no coach date of birth, only a birth place",
               context=self.href, log=log)

        records = data.get("careerRecords") or []
        if records:
            record = self.pager.get(
                _core_path(records[0].get("$ref", "")),
                base_url=_CORE_URL,
            ) or {}
            self._wins, self._losses = _record_wl(record.get("displayValue"))
        else:
            self._wins = 0
            self._losses = 0
            assume("coach_info", "wins", 0,
                   "coach profile carries no career records, so Wins and "
                   "Losses are 0",
                   context=self.href, log=log)


class player_info(abstract.player_info):
    def __init__(self, href, pager, id_cache):
        self.href = href
        self.pager = pager
        if href in id_cache.keys():
            self._id = id_cache[href]
            self._fetched = True
        else:
            # href is "/espn/athlete/<athleteId>" with no season: see
            # _player_href. Every column player_info actually stores (name,
            # birthday, college, draft) is fixed for a player's career, so the
            # unscoped core-api resource is enough, and its team/experience
            # fields are season-dependent but are not stored. Mirrors
            # coach_info's "/coaches/<id>" request below.
            parts = _href_parts(href)
            athlete_id = parts[2] if len(parts) > 2 else ""
            self.soup = {}
            if athlete_id.isdigit():
                self.soup = pager.get(
                    "/athletes/" + athlete_id,
                    base_url=_CORE_URL,
                ) or {}
            self._shoots = None
            self._name = None
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

    def _fetch(self):
        # ESPN exposes no shooting-hand data, so default to right-handed to
        # satisfy the Shoots column's CHECK constraint. Reported rather than
        # silent: every Shoots value in the database is assumed, and a whole
        # season of them is one INFO line.
        self._shoots = "R"
        assume("player_info", "shoots", "R",
               "ESPN exposes no shooting-hand data",
               context=self.href, log=log)

        data = self.soup
        self._name = data.get("fullName") or data.get("displayName") or ""
        self._birthday = str(data.get("dateOfBirth") or "")[:10]

        college_ref = (data.get("college") or {}).get("$ref", "")
        self._college = 1 if college_ref else 0
        self._high_school = 0
        assume("player_info", "high_school", 0,
               "ESPN exposes no high school field",
               context=self.href, log=log)

        draft = data.get("draft") or {}
        self._draft_year = _int(draft.get("year", 0))
        self._draft_position = _int(draft.get("selection", 0))
        draft_team = (draft.get("team") or {}).get("$ref", "")
        match = re.search(r"/teams/(\d+)", str(draft_team))
        self._draft_team = _team_name(self.pager, match.group(1)) if match else ""

        # ESPN has no debut-date field. Career seasons come from the athlete's
        # experience entry, which is what the source is able to report.
        self._career_seasons = _int((data.get("experience") or {}).get("years", 0))
        self._debut_date = ""
        assume("player_info", "debut_date", "",
               "ESPN exposes no debut date",
               context=self.href, log=log)

        team = (data.get("team") or {}).get("$ref", "")
        match = re.search(r"/teams/(\d+)", str(team))
        self._teams = _team_name(self.pager, match.group(1)) if match else ""


class team_info(abstract.team_info):
    def __init__(self, href, pager, id_cache):
        self.href = href
        self.pager = pager
        if href in id_cache.keys():
            self._id = id_cache[href]
            self._season = None
            self._fetched = True
        else:
            # href is "/espn/team/<teamId>/<season>"; the season qualifies the
            # id_cache key so each franchise gets one team ID per season.
            parts = _href_parts(href)
            team_id = parts[2] if len(parts) > 2 else ""
            self._team_id = team_id
            self._season = int(parts[3]) if len(parts) > 3 else None
            self.soup = pager.get("/teams/" + team_id, base_url=_CORE_URL) or {}
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

        team = self.soup
        if standings is not None:
            self._wins = standings["wins"]
            self._losses = standings["losses"]
            self._ranking = standings["rank"]
            self._playoff_appearance = standings["playoff"]
            self._name = standings["name"]
        else:
            # No standings for this season (a single game scraped on its own).
            self._wins = 0
            self._losses = 0
            self._ranking = 99
            self._playoff_appearance = False
            self._name = team.get("displayName", "")

        self._location = team.get("location", "")
        self._abbreviation = team.get("abbreviation", "")
        # Only a season crawl builds _SEASON_COACHES, so a game scraped on its
        # own leaves Coach_ID at 0, mirroring the standings fallback above.
        if self._season is not None:
            self._coach_href = _SEASON_COACHES.get(
                self._season, {}).get(self._team_id)
        parts = _href_parts(self.href)
        if parts and not _TEAM_NAMES.get(parts[2]):
            _TEAM_NAMES[parts[2]] = self._name


class season_info(abstract.season_info):
    def __init__(self, href, pager, id_cache):
        self.href = href
        self.pager = pager
        if href in id_cache.keys():
            self._season = id_cache[href]
            self._fetched = True
        else:
            # No page backs an ESPN season, so no request is made here; the
            # schedule and team records both come from the JSON APIs.
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
        parts = _href_parts(self.href)
        season = int(parts[-1]) if parts and parts[-1].isdigit() else None

        self._games = 0
        self._teams = 0
        # Season awards and the champion are filled from _SEASON_AWARDS after
        # the schedule and standings are read. The numeric columns stay 0 and
        # the matching hrefs stay None when ESPN has not published a season's
        # awards; hrefs must be None rather than "" because empty_href_wrap
        # only skips a None href.
        self._champion = 0
        self._finals_mvp = 0
        self._mvp = 0
        self._dpoy = 0
        self._mip = 0
        self._sixmoty = 0
        self._roty = 0
        self._rankings = {}
        self._schedule = []

        if season is None:
            self._season = 1991
            return
        self._season = season

        _REFEREE_DATA.clear()

        # Enumerate the season type by type so every event is classified before
        # any game page is read. The play-in games live in their own type, and
        # All-Star games are not in any of these buckets.
        schedule = []
        seen = set()
        for season_type in _SEASON_TYPES:
            page = 1
            while page <= _MAX_PAGES:
                href = "/seasons/%d/types/%d/events?limit=%d&page=%d" % (
                    season, season_type, _PAGE_SIZE, page,
                )
                resp = self.pager.get(href, base_url=_CORE_URL) or {}
                items = resp.get("items", []) or []
                for item in items:
                    match = re.search(r"/events/(\d+)", item.get("$ref", ""))
                    if not match:
                        continue
                    event_id = match.group(1)
                    if event_id in seen:
                        continue
                    seen.add(event_id)
                    _EVENT_TYPE[event_id] = season_type
                    schedule.append("/espn/event/" + event_id)
                if len(items) < _PAGE_SIZE:
                    break
                page += 1
        self._schedule = schedule
        self._games = len(schedule)

        # Per-season team records, keyed by the season-qualified team href so
        # team_info can look them up no matter when in the scrape the team is
        # first seen. ESPN's standings are returned in an arbitrary order, so
        # the league-wide ranking is derived by sorting all 30 teams.
        standings = {}
        rows = []
        resp = self.pager.get(
            "/standings?season=%d&seasontype=2" % season,
            base_url=_STANDINGS_URL,
        ) or {}
        for conference in resp.get("children", []) or []:
            entries = conference.get("standings", {}).get("entries", []) or []
            for entry in entries:
                team = entry.get("team", {}) or {}
                team_id = str(team.get("id", ""))
                if not team_id:
                    continue
                stats = {
                    stat.get("name"): stat.get("displayValue")
                    for stat in entry.get("stats", []) or []
                }
                rows.append({
                    "team_id": team_id,
                    "name": team.get("displayName", ""),
                    "wins": _int(stats.get("wins")),
                    "losses": _int(stats.get("losses")),
                    "seed": _int(stats.get("playoffSeed")),
                })
        rows.sort(key=lambda row: (-row["wins"], row["losses"]))
        for rank, row in enumerate(rows, 1):
            href = _team_href(row["team_id"], season)
            _TEAM_NAMES[row["team_id"]] = row["name"]
            standings[href] = {
                "wins": row["wins"],
                "losses": row["losses"],
                "rank": rank,
                "playoff": 0 < row["seed"] <= _PLAYOFF_SEED_MAX,
                "name": row["name"],
            }
        _SEASON_STANDINGS[season] = standings
        self._teams = len(standings)

        # Awards and coaches are best-effort: a season whose awards are not
        # published yet, or an endpoint that fails, must not sink the crawl.
        try:
            self._fetch_awards(season)
        except Exception as error:
            log.warning("awards for %d failed: %s", season, error)
        try:
            self._fetch_coaches(season, [row["team_id"] for row in rows])
        except Exception as error:
            log.warning("coaches for %d failed: %s", season, error)

        awards = _SEASON_AWARDS.get(season, {})
        self._champion_href = awards.get("Champion")
        self._finals_mvp_href = awards.get("Finals MVP")
        self._mvp_href = awards.get("MVP")
        self._dpoy_href = awards.get("Defensive Player of the Year")
        self._mip_href = awards.get("Most Improved Player")
        self._sixmoty_href = awards.get("Sixth Man of the Year")
        self._roty_href = awards.get("Rookie of the Year")

    def _fetch_awards(self, season):
        """Map core-api season awards onto the seven season_info columns.

        Each award's winner carries an athlete ref already in the engine's
        player-href shape, so it resolves to the same Player_ID that game data
        assigns. The Finals MVP's team ref doubles as the champion: it is the
        only request-free source of the title, because the schedule holds event
        ids rather than results. The award's own name is checked before its
        winner is trusted, so a core-api renumbering cannot attach the wrong
        trophy.
        """
        awards = {}
        for name, award_id in _AWARD_IDS.items():
            record = self.pager.get(
                "/seasons/%d/awards/%d" % (season, award_id),
                base_url=_CORE_URL,
            ) or {}
            if record.get("name") != name:
                log.warning("award %d is %r, expected %r",
                            award_id, record.get("name"), name)
                continue
            winners = record.get("winners") or []
            if not winners:
                continue
            winner = winners[0]
            athlete = re.search(r"/athletes/(\d+)",
                                (winner.get("athlete") or {}).get("$ref", ""))
            if not athlete:
                continue
            awards[name] = _player_href(athlete.group(1))
            if name == "Finals MVP":
                team = re.search(r"/teams/(\d+)",
                                 (winner.get("team") or {}).get("$ref", ""))
                if team:
                    awards["Champion"] = _team_href(team.group(1), season)
        _SEASON_AWARDS[season] = awards

    def _fetch_coaches(self, season, team_ids):
        """Map each team to its head coach href for the season.

        core-api's season-scoped coach list is deceptive: a coach profile has
        no `team` ref for roughly a quarter of the league (Redick, Fernandez,
        Christie and other recent hires), so mapping through it drops those
        teams. Asking each team for its own coaches instead is authoritative
        and costs the same one request per team. Coach hrefs are deliberately
        not season-qualified; see _SEASON_COACHES.
        """
        coaches = {}
        for team_id in team_ids:
            resp = self.pager.get(
                "/seasons/%d/teams/%s/coaches" % (season, team_id),
                base_url=_CORE_URL,
            ) or {}
            items = resp.get("items") or []
            if not items:
                continue
            person = re.search(r"/coaches/(\d+)", items[0].get("$ref", ""))
            if person:
                coaches[team_id] = "/espn/coach/" + person.group(1)
        _SEASON_COACHES[season] = coaches


class game_info(abstract.game_info):
    def __init__(self, href, pager, id_cache):
        self.href = href
        self.pager = pager
        if href in id_cache.keys():
            self._id = id_cache[href]
            self._fetched = True
        else:
            # The href is the source's own namespaced game key; the summary
            # lives on a different host, so the request is made here.
            event_id = _href_parts(href)[-1]
            self.soup = pager.get("/summary?event=" + event_id,
                                  base_url=_SITE_URL) or {}
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
            self._type = "regular"

    def _classify(self, season_type, event_id, note):
        """Set the game type from ESPN's own season type, then the gameNote
        label for the in-season tournament.

        ESPN's summary header declares the season type outright (2 regular,
        3 playoffs, 5 play-in), so a game scraped on its own still classifies
        correctly. _EVENT_TYPE, filled in by season_info for the games in a
        season crawl, is only a fallback.

        There is no in-season tournament season type: those games sit in the
        regular season bucket and are identified by their gameNote ("NBA Cup
        - Group Play", "NBA Cup Championship"). neutralSite was the old
        heuristic and is wrong in both directions: only the Las Vegas
        knockout rounds are neutral (61 of the 67 tournament games are
        played at home arenas), while the Paris and Mexico City games are
        neutral but ordinary regular season games.
        """
        if season_type is None:
            season_type = _EVENT_TYPE.get(event_id, _TYPE_REGULAR)
        if season_type == _TYPE_PLAYOFFS:
            return "playoffs", True, False, False
        if season_type == _TYPE_PLAY_IN:
            return "play-in", False, False, True
        if "NBA Cup" in note:
            return "in-season tournament", False, True, False
        return "regular", False, False, False

    def _fetch(self):
        season, season_type, competition = _summary_season(self.soup)
        if not competition or season is None:
            return
        # Excluded events (All-Star) are stopped before anything is read from
        # the payload: no field, venue, or referee side effects. A season
        # crawl never reaches this code -- game_data already refused them, so
        # link_game_data has nothing to link -- but get_game_info called
        # directly on the href must not write a row either.
        note = _game_note(self.soup)
        reason = _skip_reason(note)
        if reason:
            log.warning("skipping %s: %s; not writing game info",
                        self.href, reason)
            return
        home, away = _sides(competition)
        if not home or not away:
            return

        self._home_team_name = home.get("team", {}).get("displayName", "")
        self._home_team_href = _team_href(_team_id(home), season)
        self._away_team_name = away.get("team", {}).get("displayName", "")
        self._away_team_href = _team_href(_team_id(away), season)

        game_info = self.soup.get("gameInfo", {}) or {}
        venue = game_info.get("venue", {}) or {}
        location = venue.get("fullName", "")
        address = venue.get("address", {}) or {}
        if address.get("city"):
            location += ", " + address["city"]
        if address.get("state"):
            location += ", " + address["state"]
        self._location = location.strip(", ")

        self._attendance = _int(game_info.get("attendance", 0))

        # ESPN exposes no wall-clock game duration: a finished game's status
        # carries only STATUS_FINAL, and boxscoreMinutes is just a boolean
        # flag saying minutes are present. Recorded as 0 rather than guessed.
        self._duration = 0
        assume("game_info", "duration", 0,
               "ESPN exposes no wall-clock game duration",
               context=self.href, log=log)

        self._referee_hrefs = []
        for official in game_info.get("officials", []) or []:
            name = official.get("displayName") or official.get("fullName") or ""
            if not name:
                continue
            href = "/espn/referee/" + _slugify(name)
            if href in self._referee_hrefs:
                continue
            self._referee_hrefs.append(href)
            _REFEREE_DATA[href] = {
                "name": name,
                "number": official.get("jerseyNumber", 0),
            }

        event_id = _href_parts(self.href)[-1]
        (self._type, self._playoffs, self._in_season_tournament,
         self._play_in) = self._classify(season_type, event_id, note)

        self._date = str(competition.get("date") or "")[:10]
        self._season = season

    @property
    def home_team_href(self):
        return self._home_team_href

    @property
    def away_team_href(self):
        return self._away_team_href


class game_data(abstract.game_data):
    @classmethod
    def _finalize(cls, player_data, team_data, player_quarters, team_quarters):
        """Trim the four tables to match the schema, in place.

        The whole-game tables drop Quarter, and both team tables drop PM and
        Player_ID, because those columns do not exist on team_games /
        team_quarters. Leaving them in would make save_data build an INSERT
        against a nonexistent column.
        """
        del player_data["Quarter"]
        del team_data["Quarter"]
        team_data.pop("PM", None)
        team_data.pop("Player_ID", None)
        team_quarters.pop("PM", None)
        team_quarters.pop("Player_ID", None)
        return player_data, team_data, player_quarters, team_quarters

    @classmethod
    def _empty_tables(cls):
        """The four game tables in their final, save-ready shape.

        Built up front in __init__ as well as at the end of _fetch so that a
        game ESPN has no summary for still leaves saveable tables: get_links
        walks their keys to resolve ids, and a table with no values saves no
        rows.
        """
        return cls._finalize(*[cls.initialize_table() for _ in range(4)])

    def __init__(self, href, pager, id_cache):
        self.href = href
        self.pager = pager
        if href in id_cache.keys():
            self._fetched = True
        else:
            # Same summary URL game_info uses, and the pager cache hands back
            # the already-fetched copy when the two are read back to back.
            event_id = _href_parts(href)[-1]
            self.soup = pager.get("/summary?event=" + event_id,
                                  base_url=_SITE_URL) or {}
            self._injured = {}
            self._home_team_href = None
            self._home_abbrev = None
            self._away_team_href = None
            self._away_abbrev = None
            self._game_href = None
            self._season = None
            (self._player_data, self._team_data,
             self._player_data_quarters, self._team_data_quarters) = \
                self._empty_tables()
            self._home_win = None
            self._fetched = False

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

    @staticmethod
    def _team_stats(entry):
        """Flatten a boxscore team entry into {stat name: display value}."""
        return {
            stat.get("name"): stat.get("displayValue")
            for stat in entry.get("statistics", []) or []
        }

    def _add_team_rows(self, target, entry, home_id, home_href, away_href,
                       home_win, home_score, away_score, season, periods):
        team_href = home_href if _team_id(entry) == home_id else away_href
        opp_href = away_href if team_href == home_href else home_href
        stats = self._team_stats(entry)

        # ESPN team totals carry no minutes field, so the team's playing time
        # comes from the number of periods the game actually went to, which
        # only the header competitor's linescores record (an overtime game has
        # five entries, not four).
        made, attempted = _made_attempted(
            stats.get("fieldGoalsMade-fieldGoalsAttempted"))
        threes, three_attempts = _made_attempted(
            stats.get("threePointFieldGoalsMade-threePointFieldGoalsAttempted"))
        freethrows, freethrow_attempts = _made_attempted(
            stats.get("freeThrowsMade-freeThrowsAttempted"))

        target["Quarter"].append("whole")
        target["Seconds"].append(periods * _PERIOD_SECONDS)
        target["Threes"].append(threes)
        target["Three_Attempts"].append(three_attempts)
        target["Field_Goals"].append(made)
        target["Field_Goal_Attempts"].append(attempted)
        target["Freethrows"].append(freethrows)
        target["Freethrow_Attempts"].append(freethrow_attempts)
        target["Offensive_Rebounds"].append(_int(stats.get("offensiveRebounds")))
        target["Defensive_Rebounds"].append(_int(stats.get("defensiveRebounds")))
        target["Assists"].append(_int(stats.get("assists")))
        target["Steals"].append(_int(stats.get("steals")))
        target["Blocks"].append(_int(stats.get("blocks")))
        target["Turnovers"].append(_int(stats.get("turnovers")))
        target["Fouls"].append(_int(stats.get("fouls")))
        # Team points are not part of the boxscore stat list; they come from
        # the header score.
        target["Points"].append(
            home_score if team_href == home_href else away_score)
        target["Win"].append(home_win if team_href == home_href else not home_win)
        target["Home"].append(team_href == home_href)
        target["Team_ID"].append(team_href)
        target["Opponent_ID"].append(opp_href)
        target["Game_ID"].append(self.href)
        target["Season"].append(season)

    def _add_player_rows(self, target, group, stat_block, home_id, home_href,
                         away_href, home_win, season):
        group_id = _team_id(group)
        team_href = home_href if group_id == home_id else away_href
        opp_href = away_href if team_href == home_href else home_href

        keys = stat_block.get("keys", []) or []
        for athlete_row in stat_block.get("athletes", []) or []:
            # Injured and did-not-play players are intentionally excluded, the
            # same as game_data.injury_check does for the other sources.
            if athlete_row.get("didNotPlay"):
                continue
            athlete = athlete_row.get("athlete", {}) or {}
            athlete_id = str(athlete.get("id", ""))
            if not athlete_id:
                continue
            row = dict(zip(keys, athlete_row.get("stats") or []))

            minutes = _int(row.get("minutes", 0))
            if minutes <= 0:
                continue

            made, attempted = _made_attempted(
                row.get("fieldGoalsMade-fieldGoalsAttempted"))
            threes, three_attempts = _made_attempted(
                row.get("threePointFieldGoalsMade-threePointFieldGoalsAttempted"))
            freethrows, freethrow_attempts = _made_attempted(
                row.get("freeThrowsMade-freeThrowsAttempted"))

            target["Quarter"].append("whole")
            target["Seconds"].append(minutes * 60)
            target["Threes"].append(threes)
            target["Three_Attempts"].append(three_attempts)
            target["Field_Goals"].append(made)
            target["Field_Goal_Attempts"].append(attempted)
            target["Freethrows"].append(freethrows)
            target["Freethrow_Attempts"].append(freethrow_attempts)
            target["Offensive_Rebounds"].append(_int(row.get("offensiveRebounds")))
            target["Defensive_Rebounds"].append(_int(row.get("defensiveRebounds")))
            target["Assists"].append(_int(row.get("assists")))
            target["Steals"].append(_int(row.get("steals")))
            target["Blocks"].append(_int(row.get("blocks")))
            target["Turnovers"].append(_int(row.get("turnovers")))
            target["Fouls"].append(_int(row.get("fouls")))
            target["Points"].append(_int(row.get("points")))
            target["PM"].append(_int(row.get("plusMinus")))
            target["Win"].append(
                home_win if team_href == home_href else not home_win)
            target["Home"].append(team_href == home_href)
            target["Player_ID"].append(_player_href(athlete_id))
            target["Game_ID"].append(self.href)
            target["Season"].append(season)
            target["Team_ID"].append(team_href)
            target["Opponent_ID"].append(opp_href)

    def _fetch(self):
        season, _, competition = _summary_season(self.soup)
        if not competition or season is None:
            return

        # Excluded events (All-Star) come before the postponed check so an
        # unplayed one gets its real reason rather than "not completed". The
        # tables stay empty: link_game_data then links nothing (so no
        # game_info row is ever built), saved_any writes no rows, and
        # id_cache is left unmarked so the next run retries and logs again.
        reason = _skip_reason(_game_note(self.soup))
        if reason:
            log.warning("skipping %s: %s; not writing game data",
                        self.href, reason)
            return

        # ESPN keeps postponed fixtures as events of their own with a full
        # summary (teams, date, boxscore skeleton) but no game: status is
        # STATUS_POSTPONED with completed=false and 0-0 scores. Writing them
        # would produce a game_info row and two 0-point team_games rows for a
        # game that never happened; the rescheduled game is a separate event.
        # Deliberately fail-open: only an explicit false skips, so a payload
        # that omits the field can never silently drop a finished game.
        status = (competition.get("status") or {}).get("type") or {}
        if status.get("completed") in (False, 0):
            log.warning("skipping unfinished game %s: %s; not writing game data",
                        self.href,
                        status.get("detail") or status.get("name")
                        or "not completed")
            return

        home, away = _sides(competition)
        if not home or not away:
            return

        home_id = _team_id(home)
        away_id = _team_id(away)
        home_href = _team_href(home_id, season)
        away_href = _team_href(away_id, season)
        home_score = _int(home.get("score"))
        away_score = _int(away.get("score"))
        home_win = home_score > away_score
        # Periods actually played, from the per-quarter scores ESPN splits the
        # game into. Both sides list the same number of periods.
        periods = max(
            len(home.get("linescores", []) or []),
            len(away.get("linescores", []) or []),
        ) or 4

        boxscore = self.soup.get("boxscore", {}) or {}
        team_data = self.initialize_table()
        player_data = self.initialize_table()
        # ESPN publishes no per-quarter splits, so the quarter tables stay
        # empty. They are still fully initialized: get_links walks their keys
        # to resolve ids before saving, and a table with no values saves no
        # rows.
        team_quarters = self.initialize_table()
        player_quarters = self.initialize_table()

        for entry in boxscore.get("teams", []) or []:
            self._add_team_rows(team_data, entry, home_id, home_href,
                                away_href, home_win, home_score, away_score,
                                season, periods)

        for group in boxscore.get("players", []) or []:
            for stat_block in group.get("statistics", []) or []:
                self._add_player_rows(player_data, group, stat_block, home_id,
                                      home_href, away_href, home_win, season)

        (self._player_data, self._team_data, self._player_data_quarters,
         self._team_data_quarters) = self._finalize(
            player_data, team_data, player_quarters, team_quarters)
        self._home_win = home_win


class ESPNEngine(abstract.engine):
    def __init__(self, pager, database):
        super().__init__(pager, database)
        self._source = "espn"

    def get_season_info(self, href):
        info = self.season_info(href)
        if href not in self.season_id_cache.keys():
            return super().get_season_info(href)
        # A season already in the id_cache skips _fetch in the base class, so
        # _SEASON_STANDINGS and _EVENT_TYPE would never be built in this
        # process and any game scraped now would be misclassified. Rebuild
        # them so resumed/incremental scrapes get season-accurate rows.
        info._fetch()
        return info

    def get_id_cache(self):
        cols = ["espn", "value"]
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
