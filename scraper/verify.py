# scraper/verify.py
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

"""Existence, integrity and cross-source identity checks: bballVerify's library.

Everything here is read-only against an already-scraped database until
`clear_phantoms` is called explicitly; the CLI owns all flag handling.
Scans are set-based SQL (no network, no source code), so they work on any
database regardless of which sources filled it.

Phase 2 adds two sections on top of the Phase 1 existence checks:

* `matches` -- the same real-world team/game/player/referee reached once per
  source with different ids, matched through `identity.py`'s normalizers and
  franchise crosswalk. Confirmed pairs are data; ambiguous candidates,
  near-misses (same score, dates days apart), score conflicts and
  same-source duplicates are findings. Nothing is merged here -- that is
  Phase 3's `--fix`.
* `diffs` -- for each confirmed pair, every comparable field, with the
  `VALUE_GAPS` registry below downgrading differences a source provably
  cannot publish (ESPN's missing duration, ESPN/nba.com's missing shooting
  hand, ...) to aggregated info. A difference NOT covered by the registry is
  a finding, including `0`/empty-vs-populated: the silent-zero bug class is
  exactly what this tool exists to surface, so only an explicit, documented
  registry entry may excuse a value.

Two conventions the checks depend on:

* id_cache marks live in one of three per-source columns
  (`basketball_reference`, `nba`, `espn`); `type` says what the `value`
  means. For the entity types `value` is the issued id (looked up through
  ROW_TARGETS), for `season_info` it is the Season itself, for `game_data`
  it is the flag 1, and for `rankings` id_cache *is* the storage -- so
  rankings marks are never phantoms and game_data has no row to phantom.
* `0` and NULL in a foreign-key cell mean "unset" (what refresh_output
  pads every unwritten field to), never a real id: the orphan scan skips
  both, and so does every parent lookup.
"""

import re
import sqlite3

from . import identity
from .debug import get_logger

log = get_logger(__name__)

# The per-source id_cache columns. Hrefs are namespaced per source
# ("/espn/...", "/stats/...", "/leagues/..."), so a href search across all
# three columns cannot alias.
SOURCE_COLUMNS = ("basketball_reference", "nba", "espn")

# Report sections, in the order the CLI prints them.
SECTIONS = ("phantoms", "holes", "orphans", "invariants",
            "matches", "diffs")

# id_cache type -> (table, primary key) for every type whose value column
# points at a row. Deliberately parallel to backend_sources.abstract.ID_TABLES
# (the allocation map) but separate from it: this is a row-lookup map, so it
# also covers season_info, whose value is a Season rather than an issued id.
ROW_TARGETS = {
    "referee_info":   ("referee_info",   "Referee_ID"),
    "executive_info": ("executive_info", "Executive_ID"),
    "coach_info":     ("coach_info",     "Coach_ID"),
    "player_info":    ("player_info",    "Player_ID"),
    "team_info":      ("team_info",      "Team_ID"),
    "game_info":      ("game_info",      "Game_ID"),
    "season_info":    ("season_info",    "Season"),
}

# Where a phantom mark's id is still referenced from. A mark whose row is
# gone but whose id still has referencing rows must NOT be cleared: the
# next scrape would mint a new id, leave these rows orphaned and duplicate
# the entity. Those need the Phase 3 merge instead. season_info has no
# entry: its key is natural (the Season number), so re-scraping re-creates
# an identical row and any surviving references re-resolve -- always clear.
REFERENCED_BY = {
    "game_info": (
        ("player_games", "Game_ID"),
        ("team_games", "Game_ID"),
        ("player_quarters", "Game_ID"),
        ("team_quarters", "Game_ID"),
    ),
    "player_info": (
        ("player_games", "Player_ID"),
        ("player_quarters", "Player_ID"),
        ("season_info", "Finals_MVP"),
        ("season_info", "MVP"),
        ("season_info", "DPOY"),
        ("season_info", "MIP"),
        ("season_info", "SixMOTY"),
        ("season_info", "ROTY"),
    ),
    "team_info": (
        ("game_info", "Home_Team_ID"),
        ("game_info", "Away_Team_ID"),
        ("team_games", "Team_ID"),
        ("team_games", "Opponent_ID"),
        ("team_quarters", "Team_ID"),
        ("team_quarters", "Opponent_ID"),
        ("season_info", "Champion"),
    ),
    "referee_info": (
        ("game_info", "Referee_ID1"),
        ("game_info", "Referee_ID2"),
        ("game_info", "Referee_ID3"),
    ),
    "coach_info": (("team_info", "Coach_ID"),),
    "executive_info": (("team_info", "Executive_ID"),),
}

BOXTABLES = ("player_games", "team_games", "player_quarters", "team_quarters")

EXPECTED_TABLES = (
    "game_info", "team_info", "team_games", "team_quarters",
    "player_info", "player_games", "player_quarters",
    "season_info", "referee_info", "executive_info", "coach_info",
    "id_cache",
)

# Child column -> parent table/primary key, for the FK orphan scan. The
# schema's own FK clauses name three tables that do not exist
# (referees/executives/coaches -- SQLite never enforced them, so the typo
# was inert); the checker maps to the real table names here.
ORPHAN_EDGES = [
    ("game_info", "Home_Team_ID", "team_info", "Team_ID"),
    ("game_info", "Away_Team_ID", "team_info", "Team_ID"),
    ("game_info", "Season", "season_info", "Season"),
    ("game_info", "Referee_ID1", "referee_info", "Referee_ID"),
    ("game_info", "Referee_ID2", "referee_info", "Referee_ID"),
    ("game_info", "Referee_ID3", "referee_info", "Referee_ID"),
    ("team_info", "Season", "season_info", "Season"),
    ("team_info", "Coach_ID", "coach_info", "Coach_ID"),
    ("team_info", "Executive_ID", "executive_info", "Executive_ID"),
    ("season_info", "Champion", "team_info", "Team_ID"),
    ("season_info", "Finals_MVP", "player_info", "Player_ID"),
    ("season_info", "MVP", "player_info", "Player_ID"),
    ("season_info", "DPOY", "player_info", "Player_ID"),
    ("season_info", "MIP", "player_info", "Player_ID"),
    ("season_info", "SixMOTY", "player_info", "Player_ID"),
    ("season_info", "ROTY", "player_info", "Player_ID"),
]
for _table in ("team_games", "team_quarters", "player_games", "player_quarters"):
    ORPHAN_EDGES.append((_table, "Game_ID", "game_info", "Game_ID"))
    ORPHAN_EDGES.append((_table, "Season", "season_info", "Season"))
    ORPHAN_EDGES.append((_table, "Team_ID", "team_info", "Team_ID"))
    ORPHAN_EDGES.append((_table, "Opponent_ID", "team_info", "Team_ID"))
for _table in ("player_games", "player_quarters"):
    ORPHAN_EDGES.append((_table, "Player_ID", "player_info", "Player_ID"))

# The stat columns that sum across periods. player_* carry plus/minus,
# team_* do not have the column at all.
PLAYER_ADDITIVE = [
    "Seconds", "Threes", "Three_Attempts", "Field_Goals",
    "Field_Goal_Attempts", "Freethrows", "Freethrow_Attempts",
    "Offensive_Rebounds", "Defensive_Rebounds", "Assists", "Steals",
    "Blocks", "Turnovers", "Fouls", "Points", "PM",
]
TEAM_ADDITIVE = [c for c in PLAYER_ADDITIVE if c != "PM"]

# Plausible game duration window, in MINUTES: every source stores minutes
# (basketball_reference and nba both parse "2:15" as hours * 60 + minutes),
# and ESPN stores 0 because it publishes no wall-clock duration at all --
# that zero is a known gap reported once as info, not a failure. Negatives
# are impossible to insert only for Attendance (CHECK); Duration has no
# CHECK, so it is checked here.
DURATION_MIN = 90
DURATION_MAX = 240
ATTENDANCE_MAX = 120000

# ---------------------------------------------------------------- Phase 2


class _Any:
    """Registry sentinel: every value from this (source, table, field) is
    explained by the reason, whatever it is -- used where the column's
    *meaning* differs across sources rather than a placeholder value."""

    def __repr__(self):
        return "<any>"


ANY = _Any()

# (source, table, field) -> (set of explained raw values | ANY, reason).
# A cross-source difference where each disagreeing side is explained by its
# own registry entry degrades to an aggregated info line; a difference with
# two unexplained sides is a finding. Entries are evidence-based: they name
# a documented capability gap (see AGENTS.md), never a convenient excuse,
# and 0/'' is registered only where the source truly publishes nothing --
# the silent-zero bug class is the thing this tool hunts.
VALUE_GAPS = {
    # game_info: ESPN has no wall-clock duration at all.
    ("espn", "game_info", "Duration"):
        ({0}, "ESPN publishes no wall-clock game duration"),

    # team_info standings columns are as-of-scrape snapshots: a record or a
    # playoff flag crawled mid-season legitimately differs from one crawled
    # at the season's end, and basketball-reference never publishes a
    # league rank at all (99 is refresh_output's unset default).
    ("basketball_reference", "team_info", "League_Ranking"):
        ({99}, "basketball-reference team pages carry no league rank; "
               "99 is the unset default"),
    ("espn", "team_info", "League_Ranking"):
        ({99}, "ESPN's rank comes from the season standings overlay; "
               "a game-only scrape leaves 99"),
    ("espn", "team_info", "Wins"):
        (ANY, "records are as-of-scrape snapshots; sources crawled at "
              "different times legitimately differ"),
    ("espn", "team_info", "Losses"):
        (ANY, "records are as-of-scrape snapshots; sources crawled at "
              "different times legitimately differ"),
    ("espn", "team_info", "Playoff_Appearance"):
        (ANY, "playoff status is only known once the season ends; a "
              "game-only scrape leaves 0"),
    ("nba", "team_info", "Wins"):
        (ANY, "records are as-of-scrape snapshots; sources crawled at "
              "different times legitimately differ"),
    ("nba", "team_info", "Losses"):
        (ANY, "records are as-of-scrape snapshots; sources crawled at "
              "different times legitimately differ"),
    ("nba", "team_info", "Playoff_Appearance"):
        (ANY, "playoff status is only known once the season ends; a "
              "game-only scrape leaves 0"),
    ("basketball_reference", "team_info", "Wins"):
        (ANY, "records are as-of-scrape snapshots; sources crawled at "
              "different times legitimately differ"),
    ("basketball_reference", "team_info", "Losses"):
        (ANY, "records are as-of-scrape snapshots; sources crawled at "
              "different times legitimately differ"),
    ("basketball_reference", "team_info", "Playoff_Appearance"):
        (ANY, "playoff status is only known once the season ends; a "
              "game-only scrape leaves 0"),

    # team_info Coach/Executive are compared as resolved names, so the
    # "unset" value is None: sources with no such pages or with an overlay
    # that only a full season scrape fills register None.
    ("nba", "team_info", "Coach"):
        ({None}, "nba.com team pages carry no coach link; Coach_ID "
                 "is never set"),
    ("nba", "team_info", "Executive"):
        ({None}, "nba.com has no front-office pages; Executive_ID "
                 "is never set"),
    ("espn", "team_info", "Coach"):
        ({None}, "ESPN fills coaches from the season schedule overlay; "
                 "a game-only scrape leaves Coach_ID 0"),
    ("espn", "team_info", "Executive"):
        ({None}, "ESPN's executive_info is a stub; Executive_ID is "
                 "always 0"),

    # player_info: shooting hand and high school are never published by
    # ESPN (or nba.com for the hand), and Debut_Date is an ESPN stub.
    ("espn", "player_info", "Shoots"):
        ({"R"}, "ESPN publishes no shooting hand; R is the default"),
    ("nba", "player_info", "Shoots"):
        ({"R"}, "nba.com publishes no shooting hand; R is the default"),
    ("espn", "player_info", "High_School"):
        ({0}, "ESPN has no high-school field"),
    ("espn", "player_info", "Debut_Date"):
        ({None, "", 0}, "ESPN exposes no debut date"),
    ("nba", "player_info", "Draft_Team"):
        ({None, "", 0}, "nba.com's player payload carries draft year "
                        "and pick but no team"),

    # referee_info: both non-bbref sources publish name only.
    ("espn", "referee_info", "Number"):
        ({0}, "ESPN has no referee ids or jersey numbers"),
    ("espn", "referee_info", "Birthday"):
        ({None, "", 0}, "ESPN referee profiles carry name only"),
    ("nba", "referee_info", "Birthday"):
        ({None, "", 0}, "nba.com officials carry name and number only"),
}

# (table, field) -> reason. Never compared at all, because the column's
# convention differs per source so every value would differ: reported once
# as info when the table is compared, not per pair.
SKIP_GAPS = {
    ("team_games", "Seconds"):
        "team minutes use different conventions per source "
        "(basketball-reference/ESPN store periods * 720, nba.com sums "
        "player minutes)",
    ("team_quarters", "Seconds"):
        "team period minutes use different conventions per source "
        "(basketball-reference/ESPN store 720 per quarter, nba.com sums "
        "player minutes)",
}

# Which fields of each matched entity's info table are compared, and how.
# Columns not listed are identity columns (Name, Abbreviation, ids, the
# home/away display names) -- matching already validated those, and a
# mismatch would make the rows unmatchable rather than differ.
INFO_FIELDS = {
    "team": [("Location", "city"), ("Coach", "name"),
             ("Executive", "name"), ("Wins", "int"), ("Losses", "int"),
             ("League_Ranking", "int"), ("Playoff_Appearance", "bool"),
             ("Season", "int")],
    "game": [("Date", "date"), ("Location", "location"),
             ("Duration", "int"), ("Attendance", "int"),
             ("Season", "int"), ("Playoffs", "bool"),
             ("Play_In", "bool"), ("In_Season_Tournament", "bool"),
             ("Officials", "name_set")],
    "player": [("Shoots", "string"), ("Birthday", "birthday"),
               ("High_School", "bool"), ("College", "bool"),
               ("Draft_Position", "int"), ("Draft_Year", "int"),
               ("Draft_Team", "team_name"), ("Debut_Date", "debut")],
    "referee": [("Number", "int"), ("Birthday", "birthday")],
}

# Boxscore stat columns compared across sources, in schema order. Quarter
# tables share the whole-game column sets (Quarter is the key, not a
# field); identity columns (Season, Game_ID, Player_ID/Team_ID/Opponent_ID)
# are excluded, and team "Seconds" is listed only to be skipped by
# SKIP_GAPS above.
TEAM_BOX_FIELDS = [(c, "int") for c in
                   ("Seconds", "Threes", "Three_Attempts", "Field_Goals",
                    "Field_Goal_Attempts", "Freethrows",
                    "Freethrow_Attempts", "Offensive_Rebounds",
                    "Defensive_Rebounds", "Assists", "Steals", "Blocks",
                    "Turnovers", "Fouls", "Points")] + \
                  [("Win", "bool"), ("Home", "bool")]
PLAYER_BOX_FIELDS = [(c, "int") for c in
                     ("Seconds", "Threes", "Three_Attempts", "Field_Goals",
                      "Field_Goal_Attempts", "Freethrows",
                      "Freethrow_Attempts", "Offensive_Rebounds",
                      "Defensive_Rebounds", "Assists", "Steals", "Blocks",
                      "Turnovers", "Fouls", "Points", "PM")] + \
                    [("Win", "bool"), ("Home", "bool")]


def _source_order(item):
    """Sort key putting (id, source) pairs in a stable (source, id) order."""
    return (SOURCE_COLUMNS.index(item[1]), item[0])


def _field_key(mode, raw):
    """Normalized comparison key for one field value.

    Normalization makes format-only differences equal (ISO vs long-form
    birthdays, city-only vs city-plus-state locations, a source that
    writes 'Jr.' and one that does not), never semantic ones: two values
    that normalize apart really do disagree.
    """
    if mode == "int":
        try:
            return int(raw or 0)
        except (TypeError, ValueError):
            return str(raw)
    if mode == "bool":
        return 1 if raw else 0
    if mode in ("string", "name"):
        text = re.sub(r"\s+", " ", str(raw or "")).strip().lower()
        return text or None
    if mode == "date":
        return identity.normalize_date(raw)
    if mode == "birthday":
        return identity.normalize_birthday(raw)
    if mode == "city":
        return identity.location_city(raw)
    if mode == "location":
        return identity.normalize_location(raw)
    if mode == "team_name":
        slug = identity.alias_token(raw) if raw not in (None, "") else None
        if slug is not None:
            return ("franchise", slug)
        text = re.sub(r"\s+", " ", str(raw or "")).strip().lower()
        return ("raw", text or None)
    if mode == "debut":
        iso = identity.normalize_date(raw)
        if iso:
            return iso
        text = str(raw or "").strip()
        if re.fullmatch(r"\d{4}", text):
            return text  # a year-only debut (nba.com) compares by prefix
        return text.lower() or None
    if mode == "name_set":
        return raw if raw is not None else ()
    return raw


def _field_equiv(mode, a, b):
    """Equivalence of two keys. Only debut dates need more than ==: a
    year-only value matches any date in that year, never another year."""
    if a == b:
        return True
    if mode == "debut" and isinstance(a, str) and isinstance(b, str):
        return a.startswith(b) or b.startswith(a)
    return False


def _field_display(mode, key, raw):
    if mode == "team_name" and isinstance(key, tuple):
        return repr(key[1])  # the franchise slug reads better than "raw:..."
    if mode == "name_set":
        return "[" + ", ".join(repr(x) for x in (raw or ())) + "]"
    return repr(raw)


def _groups_fmt(groups, raws, mode):
    """'109 (espn, nba) vs 114 (basketball_reference)' for a conflict."""
    parts = []
    for group in groups:
        srcs = ", ".join(sorted(group["srcs"], key=SOURCE_COLUMNS.index))
        parts.append(f"{_field_display(mode, group['key'], raws[group['srcs'][0]])}"
                     f" ({srcs})")
    return " vs ".join(parts)


def _compare_fields(out, gap_counts, skip_notes, context, table, fields,
                    per_src):
    """Compare one entity's fields across sources; see Verifier.diffs().

    `per_src` maps source -> {label: raw value}. Values are grouped by
    normalized key; a group is *explained* when every source in it has a
    VALUE_GAPS entry matching its raw value. One or zero unexplained
    groups means every difference traces to a documented gap, so the
    event degrades to an aggregated info line (counted per excused
    source); two or more mean two unexcused sources genuinely disagree --
    a finding, including 0/''-vs-populated. That strictness is the whole
    point: only an explicit registry entry excuses a value, so the
    silent-zero bug class surfaces instead of hiding behind a loose
    convention.
    """
    # Group order drives the printed message, so normalize it: the output
    # must not depend on how the caller built the dict.
    per_src = {src: per_src[src]
               for src in sorted(
                   per_src,
                   key=lambda s: (SOURCE_COLUMNS.index(s)
                                  if s in SOURCE_COLUMNS
                                  else len(SOURCE_COLUMNS), s))}
    for label, mode in fields:
        if (table, label) in SKIP_GAPS:
            skip_notes.add((table, label))
            continue
        raws = {src: vals.get(label) for src, vals in per_src.items()}
        keys = {src: _field_key(mode, raw) for src, raw in raws.items()}

        # Equivalence groups (debut compares at year prefix, so this is
        # greedy rather than a plain set()).
        groups = []
        for src in per_src:
            for group in groups:
                if _field_equiv(mode, keys[src], group["key"]):
                    group["srcs"].append(src)
                    break
            else:
                groups.append({"key": keys[src], "srcs": [src]})
        if len(groups) <= 1:
            continue

        explained = {}
        for src in per_src:
            entry = VALUE_GAPS.get((src, table, label))
            if entry and (entry[0] is ANY or raws[src] in entry[0]):
                explained[src] = entry[1]

        unexcused = [g for g in groups
                     if not all(s in explained for s in g["srcs"])]
        if len(unexcused) >= 2:
            out.append(_finding(
                "diffs", "field_conflict",
                f"{context}: {label}: {_groups_fmt(groups, raws, mode)}"))
            continue

        anchor = unexcused[0]["key"] if unexcused else None
        for src in explained:
            if anchor is None or not _field_equiv(mode, keys[src], anchor):
                key = (src, table, label)
                gap_counts[key] = gap_counts.get(key, 0) + 1


def _finding(section, kind, message, **extra):
    out = {"section": section, "kind": kind, "severity": "finding",
           "message": message}
    out.update(extra)
    return out


def _info(section, kind, message, **extra):
    out = {"section": section, "kind": kind, "severity": "info",
           "message": message}
    out.update(extra)
    return out


def _expected_season(date):
    """Season a tip-off date implies: month >= 10 rolls into next year.

    The same rule every source uses to derive Season, and the rule the old
    soup.select('u') bug silently violated. Returns None when `date` is not
    a strict 'YYYY-MM-DD' string (the caller reports that separately).
    """
    if not isinstance(date, str) or len(date) != 10:
        return None
    if date[4] != "-" or date[7] != "-":
        return None
    try:
        year = int(date[0:4])
        month = int(date[5:7])
        day = int(date[8:10])
    except ValueError:
        return None
    if not 1 <= month <= 12 or not 1 <= day <= 31:
        return None
    return year + 1 if month >= 10 else year


class Verifier:
    """Read-only integrity checks over one scraped database.

    Holds a single connection for its lifetime; call close() (or use it as
    a context manager) when done. Every scan returns a list of finding
    dicts with at least `section`, `kind`, `severity` ("finding" or
    "info") and a human-readable `message`. Severity drives the CLI exit
    code: "info" never fails a run.
    """

    def __init__(self, database):
        self.database = database
        self._con = None
        self._ident = None  # cached cross-source identity build (Phase 2)

    # ---------- plumbing ----------

    @property
    def con(self):
        if self._con is None:
            con = self.database.give_connection()
            if con is None:
                raise ValueError("the database has no location; "
                                 "bballVerify needs a real database file")
            con.row_factory = sqlite3.Row
            self._con = con
        return self._con

    def close(self):
        if self._con is not None:
            self._con.close()
            self._con = None

    def __enter__(self):
        self.con
        return self

    def __exit__(self, *exc):
        self.close()

    def _rows(self, sql, params=()):
        return self.con.execute(sql, params).fetchall()

    def _one(self, sql, params=()):
        return self.con.execute(sql, params).fetchone()

    def missing_schema(self):
        """Expected tables this database does not have (empty = healthy)."""
        names = {r["name"] for r in
                 self._rows("SELECT name FROM sqlite_master WHERE type = 'table'")}
        return [t for t in EXPECTED_TABLES if t not in names]

    # ---------- shared lookups ----------

    def _all_marks(self):
        return self._rows(
            "SELECT rowid AS rid, basketball_reference, nba, espn, "
            "value, type FROM id_cache")

    @staticmethod
    def _mark_href(row):
        """(source column, href) a mark lives in, or (None, None)."""
        for col in SOURCE_COLUMNS:
            if row[col] is not None:
                return col, row[col]
        return None, None

    def _row_present(self, id_type, value):
        table, pk = ROW_TARGETS[id_type]
        row = self._one(f"SELECT 1 FROM {table} WHERE {pk} = ? LIMIT 1",
                        (value,))
        return row is not None

    def _dependent_count(self, id_type, value):
        total = 0
        for table, col in REFERENCED_BY.get(id_type, ()):
            row = self._one(
                f"SELECT COUNT(*) AS n FROM {table} WHERE {col} = ?",
                (value,))
            total += row["n"]
        return total

    def _box_counts(self):
        """{table: {Game_ID: row count}} for the four boxscore tables."""
        counts = {t: {} for t in BOXTABLES}
        for table in BOXTABLES:
            for r in self._rows(
                    f"SELECT Game_ID, COUNT(*) AS n FROM {table} "
                    f"GROUP BY Game_ID"):
                if r["Game_ID"] is not None:
                    counts[table][r["Game_ID"]] = r["n"]
        return counts

    def _box_children(self, game_id):
        out = {}
        for table in BOXTABLES:
            row = self._one(
                f"SELECT COUNT(*) AS n FROM {table} WHERE Game_ID = ?",
                (game_id,))
            out[table] = row["n"]
        return out

    def _game_id_for_href(self, col, href):
        """Resolve a game href to its Game_ID via the game_info mark."""
        if col is None:
            return None
        row = self._one(
            "SELECT value FROM id_cache WHERE type = 'game_info' "
            f"AND {col} = ? LIMIT 1", (href,))
        return None if row is None else row["value"]

    def _game_data_mark(self, col, href):
        """Is the game_data mark present for the same source column+href?"""
        if col is None:
            return None
        row = self._one(
            "SELECT 1 FROM id_cache WHERE type = 'game_data' "
            f"AND {col} = ? LIMIT 1", (href,))
        return row is not None

    # ---------- section 1: phantoms ----------

    def phantoms(self):
        """id_cache marks whose row is gone, and rows whose mark is gone.

        The first half is id-aware, not table-aware: a season_info row for
        a different Season does not satisfy this mark, and in a combined
        database the same real-world game has one Game_ID per source. The
        second half is the dual defect -- a row with no mark, which the
        next scrape answers by minting a fresh id and duplicating it.
        """
        out = []
        marks = self._all_marks()

        for m in marks:
            id_type = m["type"]
            # game_data is a flag (no row to phantom -- it is checked as a
            # hole instead) and rankings lives *in* id_cache, so neither
            # belongs here. Unknown types are skipped.
            if id_type not in ROW_TARGETS:
                continue
            value = m["value"]
            if self._row_present(id_type, value):
                continue
            deps = self._dependent_count(id_type, value)
            # season_info's key is natural, so re-scraping re-creates an
            # identical row and surviving references re-resolve.
            clearable = id_type == "season_info" or deps == 0
            col, href = self._mark_href(m)
            where = "" if col is None else f" ({col}={href})"
            if clearable:
                suffix = ("clearable with --clear-phantoms"
                          if id_type != "season_info"
                          else "clearable with --clear-phantoms "
                               "(re-scrape re-creates the Season row)")
            else:
                suffix = (f"{deps} referencing row(s); NOT clearable -- "
                          "needs the Phase 3 merge")
            out.append(_finding(
                "phantoms", "phantom",
                f"{id_type} value {value}{where}: row missing; {suffix}",
                type=id_type, value=value, rowid=m["rid"],
                dependencies=deps, clearable=clearable,
                **({} if col is None else {"source": col, "href": href})))

        for id_type, (table, pk) in ROW_TARGETS.items():
            marked = {m["value"] for m in marks if m["type"] == id_type}
            for r in self._rows(f"SELECT {pk} AS id FROM {table}"):
                if r["id"] in marked:
                    continue
                if id_type == "season_info":
                    # Natural key: the next scrape of that season upserts
                    # and marks -- self-healing, so info not failure.
                    out.append(_info(
                        "phantoms", "unmarked_row",
                        f"season_info row {r['id']} has no id_cache mark in "
                        "any source; it self-heals (upsert + mark) on the "
                        "next scrape of that season",
                        type=id_type, value=r["id"]))
                else:
                    out.append(_finding(
                        "phantoms", "unmarked_row",
                        f"{table} row {pk}={r['id']} has no id_cache mark; "
                        "the next scrape will mint a new id and duplicate "
                        "this row (mark repair -- Phase 3)",
                        type=id_type, value=r["id"]))
        return out

    # ---------- section 2: holes ----------

    def holes(self):
        """Expected data that is absent: games, boxscores, seasons.

        The manifest is id_cache marks plus season_info.Games -- no network,
        so games that were simply never scraped are reported (info), not
        guessed at.
        """
        out = []
        counts = self._box_counts()
        game_rows = self._rows("SELECT Game_ID, Season FROM game_info")
        present = {r["Game_ID"] for r in game_rows}

        # --- game_data marks: lying or unresolvable ---
        lying = set()
        marked = {}
        for m in self._all_marks():
            if m["type"] != "game_data":
                continue
            col, href = self._mark_href(m)
            game_id = self._game_id_for_href(col, href)
            if game_id is None:
                out.append(_finding(
                    "holes", "unresolvable_mark",
                    f"game_data mark {col}={href} cannot be resolved to a "
                    "game_info mark; its boxscore state cannot be verified "
                    "and it is not safe to clear (needs Phase 3)",
                    rowid=m["rid"]))
                continue
            if any(counts[t].get(game_id, 0) for t in BOXTABLES):
                marked[game_id] = m["rid"]
            else:
                lying.add(game_id)
                row_note = ("" if game_id in present
                            else " and the game_info row is also missing")
                out.append(_finding(
                    "holes", "lying_mark",
                    f"game_data mark {col}={href} claims game {game_id} "
                    f"complete but no boxscore rows exist{row_note}; "
                    "clearable with --clear-phantoms",
                    rowid=m["rid"], game_id=game_id, clearable=True))

        # --- per-game checks ---
        pg_players = {}
        pq_players = {}
        for r in self._rows("SELECT Game_ID, Player_ID FROM player_games"):
            pg_players.setdefault(r["Game_ID"], set()).add(r["Player_ID"])
        for r in self._rows("SELECT Game_ID, Player_ID FROM player_quarters"):
            pq_players.setdefault(r["Game_ID"], set()).add(r["Player_ID"])

        for r in game_rows:
            game_id, season = r["Game_ID"], r["Season"]
            rows = sum(counts[t].get(game_id, 0) for t in BOXTABLES)
            if rows == 0:
                if game_id in lying:
                    continue  # already reported above
                if game_id not in marked:
                    out.append(_info(
                        "holes", "unscraped",
                        f"game {game_id} (season {season}) has game_info "
                        "but no boxscore rows and no game_data mark; a "
                        "season re-scrape retries it",
                        game_id=game_id))
                continue
            if game_id not in marked:
                out.append(_finding(
                    "holes", "boxscore_unmarked",
                    f"game {game_id} has boxscore rows but no game_data "
                    "mark; a re-scrape will duplicate them (mark repair -- "
                    "Phase 3)",
                    game_id=game_id))
            teams = counts["team_games"].get(game_id, 0)
            players = counts["player_games"].get(game_id, 0)
            if teams != 2 or players == 0:
                out.append(_finding(
                    "holes", "partial_boxscore",
                    f"game {game_id}: {teams} team_games row(s) (expected "
                    f"2), {players} player_games row(s) (expected > 0)",
                    game_id=game_id))
            has_quarters = (counts["player_quarters"].get(game_id, 0) or
                            counts["team_quarters"].get(game_id, 0))
            if has_quarters:
                missing = [p for p in
                           pg_players.get(game_id, set()) -
                           pq_players.get(game_id, set())]
                if missing:
                    missing.sort(key=lambda p: (p is None, p))
                    shown = ", ".join(str(p) for p in missing[:10])
                    if len(missing) > 10:
                        shown += f", +{len(missing) - 10} more"
                    out.append(_finding(
                        "holes", "missing_quarters",
                        f"game {game_id}: {len(missing)} player(s) with "
                        f"whole-game rows but no quarter rows: {shown}",
                        game_id=game_id))

        # --- season completeness ---
        # Games semantics differ per source (basketball_reference counts
        # the regular season only, espn and nba schedules include
        # playoffs and play-in), so a partial count is informational and
        # an over-count is no finding at all.
        season_rows = {r["Season"]: r["Games"]
                       for r in self._rows("SELECT Season, Games FROM season_info")}
        game_counts = dict(self._rows(
            "SELECT Season, COUNT(*) AS n FROM game_info GROUP BY Season"))
        seen = set()
        for m in self._all_marks():
            if m["type"] != "season_info":
                continue
            season = m["value"]
            if season in seen:
                continue
            seen.add(season)
            if season not in season_rows:
                continue  # phantom; reported in phantoms
            games = season_rows[season] or 0
            have = game_counts.get(season, 0)
            if games > 0 and have == 0:
                out.append(_finding(
                    "holes", "season_empty",
                    f"season {season}: marked complete with Games={games} "
                    "but no game_info rows carry that season",
                    season=season))
            elif 0 < have < games:
                out.append(_info(
                    "holes", "season_incomplete",
                    f"season {season}: {have}/{games} games present "
                    "(expected count is source-dependent -- regular-season "
                    "vs playoffs -- so partial is informational)",
                    season=season))
        return out

    # ---------- section 3: FK orphans ----------

    def orphans(self):
        """Child rows pointing at parent ids that do not exist.

        Catches failed merges and dropped rows. NULL and 0 both mean
        "unset" (the refresh_output default) and are never orphans.
        """
        out = []
        for child, col, parent, pk in ORPHAN_EDGES:
            for r in self._rows(
                    f"SELECT c.{col} AS val, COUNT(*) AS n "
                    f"FROM {child} c LEFT JOIN {parent} p "
                    f"ON c.{col} = p.{pk} "
                    f"WHERE c.{col} IS NOT NULL AND c.{col} != 0 "
                    f"AND p.{pk} IS NULL GROUP BY c.{col}"):
                out.append(_finding(
                    "orphans", "fk_orphan",
                    f"{child}.{col} -> {parent}.{pk}: {r['n']} row(s) "
                    f"reference missing {col}={r['val']}",
                    child=child, column=col, parent=parent,
                    value=r["val"], rows=r["n"]))
        return out

    # ---------- section 4: within-source invariants ----------

    def _grouped_sums(self, table, group_cols, value_cols):
        sums = ", ".join(f"SUM({c}) AS s_{c}" for c in value_cols)
        groups = ", ".join(group_cols)
        return self._rows(
            f"SELECT {groups}, {sums} FROM {table} GROUP BY {groups}")

    def _quarter_sums(self, whole, quarters, value_cols, label):
        """Compare quarter sums against whole-game totals, per key.

        Only keys whose quarter side has rows are compared (games without
        any quarter rows -- ESPN publishes none -- are out of scope), and
        a column whose quarter sum is NULL (never written) is skipped:
        there is nothing to verify. A key missing from the quarter side
        entirely is the holes-section missing_quarters check, not ours.
        """
        out = []
        whole_rows = self._grouped_sums(
            whole, ("Game_ID", "Player_ID" if label == "player"
                    else "Team_ID"), value_cols)
        quarter_rows = self._grouped_sums(
            quarters, ("Game_ID", "Player_ID" if label == "player"
                       else "Team_ID"), value_cols)
        key_cols = ("Game_ID", "Player_ID" if label == "player" else "Team_ID")
        quarter_map = {tuple(r[c] for c in key_cols): r for r in quarter_rows
                       if r["Game_ID"] is not None}
        for r in whole_rows:
            if r["Game_ID"] is None:
                continue  # unattachable row; orphans (Phase 3) covers it
            key = tuple(r[c] for c in key_cols)
            q = quarter_map.get(key)
            if q is None:
                continue
            diffs = []
            for col in value_cols:
                qv = q[f"s_{col}"]
                if qv is None:
                    continue  # column never written on the quarter side
                wv = r[f"s_{col}"] or 0
                if qv != wv:
                    diffs.append(f"{col}: {qv} != {wv}")
            if diffs:
                out.append(_finding(
                    "invariants", "quarter_mismatch",
                    f"game {key[0]} {label} {key[1]}: quarter sums differ "
                    f"from the whole-game total ({'; '.join(diffs)}) -- the "
                    "truncated-overtime class of bug",
                    game_id=key[0], **{label: key[1]}))
        return out

    def invariants(self):
        """Cross-table consistency that needs no network.

        I1 player/team point sums, I2/I3 quarter-vs-whole totals, I4 the
        Season-from-Date month>=10 rule, I5 Duration/Attendance sanity.
        """
        out = []

        # I1: a game's player points must equal the sum of its team points.
        pg_points = {r["Game_ID"]: r["pts"]
                     for r in self._rows(
                         "SELECT Game_ID, SUM(Points) AS pts, COUNT(*) AS n "
                         "FROM player_games GROUP BY Game_ID")
                     if r["Game_ID"] is not None}
        tg_points = {r["Game_ID"]: r["pts"]
                     for r in self._rows(
                         "SELECT Game_ID, SUM(Points) AS pts, COUNT(*) AS n "
                         "FROM team_games GROUP BY Game_ID")
                     if r["Game_ID"] is not None}
        for game_id in sorted(set(pg_points) & set(tg_points)):
            if pg_points[game_id] != tg_points[game_id]:
                out.append(_finding(
                    "invariants", "points_mismatch",
                    f"game {game_id}: player_points "
                    f"{pg_points[game_id]} != team_points "
                    f"{tg_points[game_id]}",
                    game_id=game_id))

        # I2/I3: quarter sums must equal whole-game totals.
        out.extend(self._quarter_sums("player_games", "player_quarters",
                                      PLAYER_ADDITIVE, "player"))
        out.extend(self._quarter_sums("team_games", "team_quarters",
                                      TEAM_ADDITIVE, "team"))

        # I4/I5: Season must match Date's month>=10 rule; duration and
        # attendance must be plausible.
        zero_duration = []
        for r in self._rows(
                "SELECT Game_ID, Date, Season, Duration, Attendance "
                "FROM game_info"):
            game_id = r["Game_ID"]
            expected = _expected_season(r["Date"])
            if expected is None:
                out.append(_finding(
                    "invariants", "bad_date",
                    f"game {game_id}: Date {r['Date']!r} is not a "
                    "YYYY-MM-DD string",
                    game_id=game_id))
            elif expected != r["Season"]:
                out.append(_finding(
                    "invariants", "season_mismatch",
                    f"game {game_id}: Date {r['Date']} implies season "
                    f"{expected}, stored Season={r['Season']}",
                    game_id=game_id))
            duration = 0 if r["Duration"] is None else r["Duration"]
            if duration < 0 or (duration > 0 and
                                not DURATION_MIN <= duration <= DURATION_MAX):
                out.append(_finding(
                    "invariants", "duration_implausible",
                    f"game {game_id}: Duration {duration} outside "
                    f"{DURATION_MIN}-{DURATION_MAX} minutes",
                    game_id=game_id))
            elif duration == 0:
                zero_duration.append(game_id)
            attendance = r["Attendance"]
            if attendance is not None and attendance > ATTENDANCE_MAX:
                out.append(_finding(
                    "invariants", "attendance_implausible",
                    f"game {game_id}: Attendance {attendance} exceeds "
                    f"{ATTENDANCE_MAX}",
                    game_id=game_id))
        if zero_duration:
            # ESPN's known gap, reported once: 0 = "no duration published",
            # not a corrupt number.
            shown = ", ".join(str(g) for g in zero_duration[:5])
            if len(zero_duration) > 5:
                shown += f", +{len(zero_duration) - 5} more"
            out.append(_info(
                "invariants", "no_duration",
                f"Duration=0 on {len(zero_duration)} game(s) ({shown}): "
                "ESPN publishes no wall-clock game duration",
                games=zero_duration))
        return out

    # ---------- section 5: cross-source identity ----------

    def _identity(self):
        """Match every entity across sources; built once, then cached.

        Returns a dict:

        * `findings`  -- the matches section's findings (ambiguous
          candidates, near-misses, score conflicts, duplicates,
          unresolvable rows), each a report dict.
        * `clusters`  -- confirmed multi-source clusters:
          {"entity", "rows": [(id, source), ...], "note"}. One row per
          source by construction; same-source duplicates were flagged as
          findings and their first row is used.
        * `pairs`     -- (entity, a_id, a_src, b_id, b_src, note), every
          cross-source combination inside a cluster (a 3-source game
          yields 3 pairs).
        * `summary`   -- confirmed pair count per entity.
        * `rows`/`attrib`   -- per-table row and id_cache-attribution
          lookups the differ reuses.
        * `team_slug` -- Team_ID -> franchise slug (resolved rows only).
        * `games`     -- Game_ID -> {"id","src","date","home","away",
          "season","score"} for the resolvable games (score is
          (home, away) points from team_games, or None).
        * `player_map` -- Player_ID -> cluster index for players matched
          across sources, so boxscore rows can join on identity.

        Read-only; no network.
        """
        if self._ident is None:
            self._ident = self._build_identity()
        return self._ident

    def _build_identity(self):
        marks_by_type = {}
        for m in self._all_marks():
            marks_by_type.setdefault(m["type"], []).append(m)

        findings = []
        clusters = []
        pairs = []
        rows = {}
        attrib = {}

        def attributed(id_type, table, pk):
            """All rows of `table` plus their id_cache attribution.

            Rows with no mark at all are excluded from the attribution
            (their defect is section 1's business, and an unattributable
            row cannot be matched to a source); rows themselves are kept
            whole so exists(key=) can find row-only entities.
            """
            table_rows = {r[pk]: r for r in self._rows(f"SELECT * FROM {table}")}
            table_attrib = {}
            for m in marks_by_type.get(id_type, ()):
                col, href = self._mark_href(m)
                if col is None:
                    continue
                entry = table_attrib.setdefault(
                    m["value"], {"source": None, "href": None,
                                 "marked": False})
                entry["marked"] = True
                if entry["source"] is None:
                    entry["source"], entry["href"] = col, href
            rows[table] = table_rows
            kept = {k: v for k, v in table_attrib.items()
                    if k in table_rows and v["source"] is not None}
            attrib[table] = kept
            return table_rows, kept

        def add_cluster(entity, group_rows, note):
            group_rows = sorted(group_rows, key=_source_order)
            clusters.append({"entity": entity, "rows": group_rows,
                             "note": note})
            for i in range(len(group_rows)):
                for j in range(i + 1, len(group_rows)):
                    a, b = group_rows[i], group_rows[j]
                    if a[1] != b[1]:
                        pairs.append((entity, a[0], a[1], b[0], b[1], note))
            return len(clusters) - 1

        def split_group(entity, group_rows, what):
            """Flag same-source duplicates; True if >= 2 sources present."""
            by_src = {}
            for item in group_rows:
                by_src.setdefault(item[1], []).append(item)
            for src, items in by_src.items():
                if len(items) > 1:
                    ids = ", ".join(str(i) for i, _ in items)
                    findings.append(_finding(
                        "matches", "duplicate",
                        f"{entity}: source {src} has {len(items)} rows "
                        f"for {what} (ids {ids}) -- possible duplicate "
                        "(Phase 3 merge)"))
            return len(by_src) >= 2

        # ----- teams -----

        team_rows, team_attrib = attributed(
            "team_info", "team_info", "Team_ID")
        team_slug = {}
        learned = {}
        unknown_teams = []

        for tid in sorted(team_rows):
            a = team_attrib.get(tid)
            if a is None:
                continue
            row = team_rows[tid]
            slug = identity.resolve_team(href=a["href"], name=row["Name"],
                                         abbrev=row["Abbreviation"])
            if slug is not None:
                team_slug[tid] = slug
                if a["href"]:
                    for col, pattern in (("nba", identity.NBA_TEAM_RE),
                                         ("espn", identity.ESPN_TEAM_RE)):
                        if a["source"] == col:
                            m = pattern.match(a["href"])
                            if m:
                                learned[(col, m.group(1))] = slug
        # Second pass: a row whose own fields resolve to nothing (a failed
        # fetch, or an abbreviation the crosswalk does not know) falls back
        # to its source-specific href id, learned from the sibling rows
        # that did resolve -- so no numeric id needs hardcoding here.
        for tid in sorted(team_rows):
            if tid in team_slug or tid not in team_attrib:
                continue
            a = team_attrib[tid]
            row = team_rows[tid]
            slug = None
            if a["source"] in ("nba", "espn") and a["href"]:
                pattern = (identity.NBA_TEAM_RE if a["source"] == "nba"
                           else identity.ESPN_TEAM_RE)
                m = pattern.match(a["href"])
                if m:
                    slug = learned.get((a["source"], m.group(1)))
            if slug is not None:
                team_slug[tid] = slug
            else:
                unknown_teams.append(
                    (tid, a["source"], row["Name"], row["Abbreviation"]))

        if unknown_teams:
            shown = ", ".join(
                f"{tid} ({src} name={name!r} abbrev={abbrev!r})"
                for tid, src, name, abbrev in unknown_teams[:8])
            if len(unknown_teams) > 8:
                shown += f", +{len(unknown_teams) - 8} more"
            findings.append(_info(
                "matches", "unknown_team",
                f"{len(unknown_teams)} team row(s) resolve to no franchise "
                f"in the crosswalk; excluded from matching: {shown}",
                count=len(unknown_teams)))

        team_groups = {}
        for tid, slug in team_slug.items():
            season = team_rows[tid]["Season"]
            team_groups.setdefault((slug, season), []).append(
                (tid, team_attrib[tid]["source"]))
        for (slug, season), group in sorted(team_groups.items(),
                                            key=lambda kv: str(kv[0])):
            if split_group("team", group, f"{slug} season {season}"):
                add_cluster("team", group,
                            f"franchise {slug} season {season}")

        # ----- games -----

        game_rows, game_attrib = attributed(
            "game_info", "game_info", "Game_ID")
        home_pts, away_pts = {}, {}
        for r in self._rows("SELECT Game_ID, Home, Points FROM team_games"):
            gid = r["Game_ID"]
            if gid is None:
                continue
            if r["Home"]:
                home_pts[gid] = r["Points"]
            else:
                away_pts[gid] = r["Points"]

        games = {}
        skip_teams, skip_dates = [], []
        for gid in sorted(game_rows):
            a = game_attrib.get(gid)
            if a is None:
                continue
            row = game_rows[gid]
            date = identity.normalize_date(row["Date"])
            home = team_slug.get(row["Home_Team_ID"])
            away = team_slug.get(row["Away_Team_ID"])
            if home is None or away is None:
                skip_teams.append((gid, a["source"]))
                continue
            if date is None:
                skip_dates.append((gid, a["source"], row["Date"]))
                continue
            hp, ap = home_pts.get(gid), away_pts.get(gid)
            games[gid] = {
                "id": gid, "src": a["source"], "date": date,
                "home": home, "away": away, "season": row["Season"],
                "score": None if hp is None or ap is None else (hp, ap),
            }

        if skip_teams:
            shown = ", ".join(f"{g} ({s})" for g, s in skip_teams[:8])
            if len(skip_teams) > 8:
                shown += f", +{len(skip_teams) - 8} more"
            findings.append(_info(
                "matches", "unmatched",
                f"{len(skip_teams)} game(s) skipped from matching: team id "
                f"resolves to no franchise: {shown}",
                count=len(skip_teams)))
        if skip_dates:
            shown = ", ".join(f"{g} ({s} {d!r})"
                              for g, s, d in skip_dates[:8])
            if len(skip_dates) > 8:
                shown += f", +{len(skip_dates) - 8} more"
            findings.append(_info(
                "matches", "unmatched",
                f"{len(skip_dates)} game(s) skipped from matching: "
                f"unparseable Date: {shown}", count=len(skip_dates)))

        def classify(a, b):
            """Match tier for a cross-source candidate pair, or None.

            With scores on both sides the score is the stronger evidence:
            identical scores within a day is one game (the +/- 1 day
            tolerance covers a source's off-by-one Date, which the diffs
            section then reports as a field conflict); identical scores
            days apart is a near-miss finding; the same date and matchup
            with *different* scores cannot be two NBA games, so it is a
            score conflict. Without scores only an exact date can confirm,
            and a nearby date stays an unconfirmed candidate.
            """
            d = identity.day_diff(a["date"], b["date"])
            sa, sb = a["score"], b["score"]
            if sa is not None and sb is not None:
                if sa == sb:
                    if d is not None and d <= 1:
                        return ("confirmed", "score + date within a day")
                    if d is not None and d <= 7:
                        return ("near_miss", None)
                    return None
                if d == 0:
                    return ("score_conflict", None)
                return None
            if d == 0:
                return ("confirmed", "scoreless; same date")
            if d is not None and d <= 7:
                return ("unconfirmed", None)
            return None

        def edge_finding(kind, a, b):
            d = identity.day_diff(a["date"], b["date"])
            matchup = f"{a['home']} vs {a['away']}"
            if kind == "near_miss":
                findings.append(_finding(
                    "matches", "near_miss",
                    f"game {a['id']} ({a['src']}, {a['date']}) and game "
                    f"{b['id']} ({b['src']}, {b['date']}): same matchup "
                    f"{matchup} and identical score {a['score']} but dates "
                    f"{d} day(s) apart -- one source's Date is suspect; "
                    "report-only"))
            elif kind == "score_conflict":
                findings.append(_finding(
                    "matches", "score_conflict",
                    f"game {a['id']} ({a['src']}) and game {b['id']} "
                    f"({b['src']}): same date {a['date']} and matchup "
                    f"{matchup} but final scores differ ({a['src']} "
                    f"{a['score'][0]}-{a['score'][1]}, {b['src']} "
                    f"{b['score'][0]}-{b['score'][1]})"))
            elif kind == "unconfirmed":
                findings.append(_info(
                    "matches", "unconfirmed_candidate",
                    f"game {a['id']} ({a['src']}, {a['date']}) and game "
                    f"{b['id']} ({b['src']}, {b['date']}): same matchup "
                    f"{matchup} {d} day(s) apart but no boxscore scores "
                    "to disambiguate; unconfirmed"))

        by_src = {}
        for g in games.values():
            by_src.setdefault(g["src"], []).append(g)
        srcs = sorted(by_src, key=SOURCE_COLUMNS.index)

        def gkey(g):
            return (SOURCE_COLUMNS.index(g["src"]), g["id"])

        confirmed_edges = []  # (a, b, tier)
        for i, s1 in enumerate(srcs):
            for s2 in srcs[i + 1:]:
                index = {}
                for g in by_src[s2]:
                    index.setdefault((g["home"], g["away"]), []).append(g)
                cand1, cand2 = {}, {}
                for a in by_src[s1]:
                    for b in index.get((a["home"], a["away"]), ()):
                        result = classify(a, b)
                        if result is None:
                            continue
                        kind, tier = result
                        if kind == "confirmed":
                            cand1.setdefault(a["id"], []).append(b)
                            cand2.setdefault(b["id"], []).append((a, tier))
                        else:
                            edge_finding(kind, a, b)
                # A pair is confirmed only when each side has exactly one
                # candidate in the other source (mutual singularity);
                # anything busier is reported as ambiguous instead.
                for gid_a, bs in sorted(cand1.items()):
                    if len(bs) > 1:
                        a = games[gid_a]
                        listed = ", ".join(f"{b['id']} ({b['src']})"
                                           for b in sorted(bs, key=gkey))
                        findings.append(_finding(
                            "matches", "ambiguous",
                            f"game {a['id']} ({a['src']}, {a['date']}, "
                            f"{a['home']} vs {a['away']}) matches "
                            f"{len(bs)} {s2} game(s): {listed} -- "
                            "ambiguous, report-only"))
                for gid_b, als in sorted(cand2.items()):
                    b = games[gid_b]
                    if len(als) > 1:
                        listed = ", ".join(
                            f"{a['id']} ({a['src']})"
                            for a, _ in sorted(als, key=lambda t: gkey(t[0])))
                        findings.append(_finding(
                            "matches", "ambiguous",
                            f"game {b['id']} ({b['src']}, {b['date']}, "
                            f"{b['home']} vs {b['away']}) matches "
                            f"{len(als)} {s1} game(s): {listed} -- "
                            "ambiguous, report-only"))
                    elif len(cand1.get(als[0][0]["id"], ())) == 1:
                        confirmed_edges.append((als[0][0], b, als[0][1]))

        # Same-source duplicates: two rows for one matchup on one day. An
        # NBA game is never played twice on the same date, so the date
        # check alone is enough and the scores need not agree.
        for s in srcs:
            index = {}
            for g in by_src[s]:
                index.setdefault((g["home"], g["away"]), []).append(g)
            for bucket in index.values():
                for x in range(len(bucket)):
                    for y in range(x + 1, len(bucket)):
                        a, b = bucket[x], bucket[y]
                        if identity.day_diff(a["date"], b["date"]) == 0:
                            findings.append(_finding(
                                "matches", "duplicate",
                                f"game: source {s} has two game_info rows "
                                f"for {a['home']} vs {a['away']} on "
                                f"{a['date']} (ids {a['id']}, {b['id']}) "
                                "-- possible duplicate (Phase 3 merge)"))

        parent = {}

        def find(node):
            parent.setdefault(node, node)
            while parent[node] != node:
                parent[node] = parent[parent[node]]
                node = parent[node]
            return node

        def union(x, y):
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[rx] = ry

        tier_by_id = {}
        for g in games.values():
            find(("game", g["id"]))
        for a, b, tier in confirmed_edges:
            union(("game", a["id"]), ("game", b["id"]))
            tier_by_id.setdefault(a["id"], set()).add(tier)
            tier_by_id.setdefault(b["id"], set()).add(tier)

        game_groups = {}
        for g in games.values():
            game_groups.setdefault(find(("game", g["id"])), []).append(
                (g["id"], g["src"]))
        for members in game_groups.values():
            if len({s for _, s in members}) < 2:
                continue
            sample = games[members[0][0]]
            tiers = set()
            for gid, _ in members:
                tiers |= tier_by_id.get(gid, set())
            note = f"{sample['home']} vs {sample['away']} {sample['date']}"
            if tiers:
                note += f" [{'; '.join(sorted(tiers))}]"
            add_cluster("game", members, note)

        # ----- players -----

        player_rows, player_attrib = attributed(
            "player_info", "player_info", "Player_ID")
        player_map = {}
        by_pname = {}
        empty_players = []
        for pid in sorted(player_rows):
            a = player_attrib.get(pid)
            if a is None:
                continue
            name = identity.normalize_name(player_rows[pid]["Name"])
            if not name:
                empty_players.append((pid, a["source"]))
                continue
            by_pname.setdefault(name, []).append(pid)

        def cluster_players(pids, what, note):
            group = [(p, player_attrib[p]["source"]) for p in pids]
            if split_group("player", group, what):
                idx = add_cluster("player", group, note)
                for p in pids:
                    player_map[p] = idx
                return idx
            return None

        for name in sorted(by_pname):
            pids = by_pname[name]
            bdays = {identity.normalize_birthday(player_rows[p]["Birthday"])
                     for p in pids}
            bdays.discard(None)
            if len(bdays) <= 1:
                # One person (or nobody in this group has a birthday):
                # name plus at most one distinct birthday cannot collide.
                bday = next(iter(bdays), None)
                cluster_players(
                    pids, f"'{name}'" + (f" birthday {bday}" if bday else ""),
                    f"name '{name}', birthday {bday or 'unknown'}")
                continue
            # Several distinct birthdays under one name: distinct people.
            # Rows with a birthday cluster within it; rows without stay
            # unresolvable and are reported as ambiguous.
            by_bday, missing = {}, []
            for p in pids:
                bday = identity.normalize_birthday(
                    player_rows[p]["Birthday"])
                if bday is None:
                    missing.append(p)
                else:
                    by_bday.setdefault(bday, []).append(p)
            for bday in sorted(by_bday):
                cluster_players(by_bday[bday], f"'{name}' birthday {bday}",
                                f"name '{name}', birthday {bday}")
            group_srcs = {player_attrib[p]["source"] for p in pids}
            if missing and len(group_srcs) >= 2:
                for p in missing:
                    cands = ", ".join(
                        f"{q} ({player_attrib[q]['source']}, "
                        f"{identity.normalize_birthday(player_rows[q]['Birthday'])})"
                        for q in pids if q != p)
                    findings.append(_finding(
                        "matches", "ambiguous",
                        f"player {p} ({player_attrib[p]['source']}, "
                        f"{player_rows[p]['Name']!r}) has no Birthday "
                        f"while same-name players do ({cands}) -- "
                        "ambiguous, report-only"))

        if empty_players:
            shown = ", ".join(f"{p} ({s})" for p, s in empty_players[:8])
            if len(empty_players) > 8:
                shown += f", +{len(empty_players) - 8} more"
            findings.append(_info(
                "matches", "unmatched",
                f"{len(empty_players)} player row(s) with an empty Name "
                f"excluded from matching: {shown}",
                count=len(empty_players)))

        # ----- referees -----

        ref_rows, ref_attrib = attributed(
            "referee_info", "referee_info", "Referee_ID")
        by_rname = {}
        empty_refs = []
        for rid in sorted(ref_rows):
            a = ref_attrib.get(rid)
            if a is None:
                continue
            name = identity.normalize_name(ref_rows[rid]["Name"])
            if not name:
                empty_refs.append((rid, a["source"]))
                continue
            by_rname.setdefault(name, []).append(rid)

        for name in sorted(by_rname):
            group = [(r, ref_attrib[r]["source"])
                     for r in by_rname[name]]
            by_src_g = {}
            for item in group:
                by_src_g.setdefault(item[1], []).append(item)
            for src, items in by_src_g.items():
                if len(items) > 1:
                    # ESPN keys referees by a name slug, so two rows with
                    # one name in one source are a collision or a repeat.
                    ids = ", ".join(str(r) for r, _ in items)
                    findings.append(_finding(
                        "matches", "ambiguous",
                        f"referee {name!r}: source {src} has {len(items)} "
                        f"rows (ids {ids}) -- ambiguous (duplicate or name "
                        "collision), report-only"))
            singles = [item for items in by_src_g.values()
                       if len(items) == 1 for item in items]
            if len({s for _, s in singles}) >= 2:
                add_cluster("referee", singles, f"name {name!r}")

        if empty_refs:
            shown = ", ".join(f"{r} ({s})" for r, s in empty_refs[:8])
            if len(empty_refs) > 8:
                shown += f", +{len(empty_refs) - 8} more"
            findings.append(_info(
                "matches", "unmatched",
                f"{len(empty_refs)} referee row(s) with an empty Name "
                f"excluded from matching: {shown}", count=len(empty_refs)))

        # Coach and executive matching is deliberately deferred (Phase 2
        # scope is teams, games, players and referees); their rows are
        # still attributed here so exists(key=) can find them.

        attributed("coach_info", "coach_info", "Coach_ID")
        attributed("executive_info", "executive_info", "Executive_ID")
        attributed("season_info", "season_info", "Season")

        summary = {"team": 0, "game": 0, "player": 0, "referee": 0}
        for entity, *_ in pairs:
            summary[entity] += 1

        return {"findings": findings, "clusters": clusters, "pairs": pairs,
                "summary": summary, "rows": rows, "attrib": attrib,
                "team_slug": team_slug, "games": games,
                "player_map": player_map}

    def matches(self, show_pairs = False):
        """Cross-source identity: which rows are the same real entity.

        Read-only, report-only -- nothing is merged (that is Phase 3's
        --fix). Confirmed pairs print as one summary count unless
        show_pairs lists them individually; everything that could not be
        confirmed -- ambiguous candidate sets, same-score near-misses,
        score conflicts, same-source duplicates, unresolvable rows --
        prints as findings or aggregated info.
        """
        ident = self._identity()
        out = list(ident["findings"])
        if show_pairs:
            for entity, a_id, a_src, b_id, b_src, note in ident["pairs"]:
                out.append(_info(
                    "matches", "pair",
                    f"{entity} {a_id} ({a_src}) = {b_id} ({b_src}) "
                    f"[{note}]"))
        summary = ident["summary"]
        counts = ", ".join(f"{k}: {v}" for k, v in summary.items())
        hint = "" if show_pairs or not ident["pairs"] else \
            " (use --show-pairs to list them)"
        out.append(_info(
            "matches", "summary",
            f"confirmed cross-source pairs: {counts}{hint}",
            **summary))
        return out

    # ---------- section 6: field differ ----------

    def diffs(self):
        """Field-level differences between confirmed cross-source pairs.

        Info tables: each cluster's comparable fields (INFO_FIELDS), with
        VALUE_GAPS downgrading a difference whose disagreeing sides are
        all individually excused to aggregated info; two unexcused sides
        disagreeing is a finding. Boxscore tables: rows joined per game
        (teams by home/away side, players and quarters by matched
        identity plus period) and every stat column compared, where both
        sources have rows. season_info is excluded: its rows are shared
        across sources by the upsert, so they are one row by construction.
        """
        ident = self._identity()
        out = []
        gap_counts = {}
        skip_notes = set()
        quarter_absent = {"player_quarters": 0, "team_quarters": 0}

        ref_names = {r["Referee_ID"]: r["Name"] for r in
                     self._rows("SELECT Referee_ID, Name FROM referee_info")}
        coach_names = {r["Coach_ID"]: r["Name"] for r in
                       self._rows("SELECT Coach_ID, Name FROM coach_info")}
        exec_names = {r["Executive_ID"]: r["Name"] for r in
                      self._rows("SELECT Executive_ID, Name "
                                 "FROM executive_info")}

        def name_or_none(names, i):
            # 0/NULL in an FK cell means unset, never a real id.
            if i in (None, 0):
                return None
            return names.get(i)

        entity_table = {"team": "team_info", "game": "game_info",
                        "player": "player_info", "referee": "referee_info"}

        def info_values(entity, row):
            if entity == "team":
                return {"Location": row["Location"],
                        "Coach": name_or_none(coach_names,
                                              row["Coach_ID"]),
                        "Executive": name_or_none(exec_names,
                                                  row["Executive_ID"]),
                        "Wins": row["Wins"], "Losses": row["Losses"],
                        "League_Ranking": row["League_Ranking"],
                        "Playoff_Appearance": row["Playoff_Appearance"],
                        "Season": row["Season"]}
            if entity == "game":
                officials = tuple(sorted(
                    identity.normalize_name(ref_names[g])
                    for g in (row["Referee_ID1"], row["Referee_ID2"],
                              row["Referee_ID3"])
                    if g and ref_names.get(g)))
                return {"Date": row["Date"], "Location": row["Location"],
                        "Duration": row["Duration"],
                        "Attendance": row["Attendance"],
                        "Season": row["Season"],
                        "Playoffs": row["Playoffs"],
                        "Play_In": row["Play_In"],
                        "In_Season_Tournament":
                            row["In_Season_Tournament"],
                        "Officials": officials}
            if entity == "player":
                return {k: row[k] for k in
                        ("Shoots", "Birthday", "High_School", "College",
                         "Draft_Position", "Draft_Team", "Draft_Year",
                         "Debut_Date")}
            return {"Number": row["Number"], "Birthday": row["Birthday"]}

        # ----- info tables -----

        for cluster in ident["clusters"]:
            entity = cluster["entity"]
            table = entity_table[entity]
            per_src = {}
            for row_id, src in cluster["rows"]:
                if src in per_src:
                    continue  # same-source duplicate: already a finding
                per_src[src] = info_values(entity, ident["rows"][table][row_id])
            if len(per_src) < 2:
                continue
            context = f"{table} rows " + ", ".join(
                f"{i} ({s})"
                for i, s in sorted(cluster["rows"], key=_source_order))
            _compare_fields(out, gap_counts, skip_notes, context, table,
                            INFO_FIELDS[entity], per_src)

        # ----- boxscore tables -----

        for cluster in ident["clusters"]:
            if cluster["entity"] != "game":
                continue
            ids = {}
            for row_id, src in cluster["rows"]:
                ids.setdefault(src, row_id)
            if len(ids) < 2:
                continue
            context = ", ".join(
                f"{gid} ({src})"
                for src, gid in sorted(ids.items(),
                                       key=lambda kv:
                                       SOURCE_COLUMNS.index(kv[0])))

            def fetch(table):
                got = {}
                for src, gid in ids.items():
                    got[src] = self._rows(
                        f"SELECT * FROM {table} WHERE Game_ID = ?", (gid,))
                return {src: rs for src, rs in got.items() if rs}

            tg = fetch("team_games")
            if len(tg) >= 2:
                for homeflag in (0, 1):
                    per_src = {}
                    for src, table_rows in tg.items():
                        row = next((r for r in table_rows
                                    if r["Home"] == homeflag), None)
                        if row is not None:
                            per_src[src] = dict(row)
                    if len(per_src) < 2:
                        continue
                    side = "home" if homeflag else "away"
                    _compare_fields(
                        out, gap_counts, skip_notes,
                        f"team_games ({side}) rows {context}",
                        "team_games", TEAM_BOX_FIELDS, per_src)

            pg = fetch("player_games")
            if len(pg) >= 2:
                keyed = {}
                for src, table_rows in pg.items():
                    for row in table_rows:
                        pidx = ident["player_map"].get(row["Player_ID"])
                        key = (("matched", pidx) if pidx is not None
                               else ("solo", src, row["Player_ID"]))
                        keyed.setdefault(key, {})[src] = row
                one_sided = 0
                for key, per_src in keyed.items():
                    if len(per_src) < 2:
                        one_sided += 1
                        continue
                    if key[0] == "matched":
                        desc = "player " + ", ".join(
                            f"{i} ({s})"
                            for i, s in sorted(
                                ident["clusters"][key[1]]["rows"],
                                key=_source_order))
                    else:
                        desc = f"player {key[2]} ({key[1]})"
                    _compare_fields(
                        out, gap_counts, skip_notes,
                        f"player_games rows {context} {desc}",
                        "player_games", PLAYER_BOX_FIELDS,
                        {s: dict(r) for s, r in per_src.items()})
                if one_sided:
                    out.append(_info(
                        "diffs", "one_sided_rows",
                        f"game rows {context}: {one_sided} player_games "
                        "row(s) present in only one source (DNP/roster "
                        "listing differences are normal)"))

            for table in ("team_quarters", "player_quarters"):
                whole = tg if table == "team_quarters" else pg
                qs = fetch(table)
                if len(qs) < 2:
                    if qs and len(whole) >= 2:
                        # one source has quarter rows for this game and
                        # another has whole-game rows but none
                        quarter_absent[table] += 1
                    continue
                keyed = {}
                for src, table_rows in qs.items():
                    for row in table_rows:
                        if table == "team_quarters":
                            key = (row["Home"], row["Quarter"])
                        else:
                            pidx = ident["player_map"].get(
                                row["Player_ID"])
                            key = ((("matched", pidx) if pidx is not None
                                    else ("solo", src, row["Player_ID"])),
                                   row["Quarter"])
                        keyed.setdefault(key, {})[src] = row
                fields = (TEAM_BOX_FIELDS if table == "team_quarters"
                          else PLAYER_BOX_FIELDS)
                for key, per_src in keyed.items():
                    if len(per_src) < 2:
                        continue  # one-sided period row: not a diff
                    if table == "team_quarters":
                        desc = f"side {key[0]} quarter {key[1]}"
                    elif key[0][0] == "matched":
                        desc = ("player " + ", ".join(
                            f"{i} ({s})"
                            for i, s in sorted(
                                ident["clusters"][key[0][1]]["rows"],
                                key=_source_order))
                            + f" quarter {key[1]}")
                    else:
                        desc = (f"player {key[0][2]} ({key[0][1]}) "
                                f"quarter {key[1]}")
                    _compare_fields(
                        out, gap_counts, skip_notes,
                        f"{table} rows {context} {desc}", table, fields,
                        {s: dict(r) for s, r in per_src.items()})

        # ----- aggregated known-gap and convention notes -----

        for (src, table, label), n in sorted(gap_counts.items()):
            out.append(_info(
                "diffs", "known_gap",
                f"{src} {table}.{label}: {n} cross-source difference(s) "
                f"explained: {VALUE_GAPS[(src, table, label)][1]}",
                source=src, table=table, field=label, count=n))
        for table, label in sorted(skip_notes):
            out.append(_info(
                "diffs", "known_gap",
                f"{table}.{label} not compared across sources: "
                f"{SKIP_GAPS[(table, label)]}"))
        for table, n in sorted(quarter_absent.items()):
            if n:
                out.append(_info(
                    "diffs", "known_gap",
                    f"{table}: quarter rows present for only one source "
                    f"on {n} game(s); not compared (ESPN publishes no "
                    "quarter splits at all; within-source quarter "
                    "coverage is the holes section's missing_quarters)"))
        return out

    # ---------- exists() API ----------

    def exists(self, type, href = None, id = None, key = None):
        """Is one entity marked, present, or both?

            exists(type, href = "/espn/event/401704628")
            exists(type, id = 17)
            exists("game_info", key = {"home": "lakers", "away": "spurs",
                                       "date": "2024-10-22"})
            exists("player_info", key = {"name": "Jayson Tatum",
                                         "birthday": "1998-03-03"})

        The href/id shape returns a dict: `marked` (an id_cache mark
        exists), `row_present` (the target table has the row), `marks`
        (each mark with its source column and href), `value` (the
        resolved id), and `children` (dependent row counts -- boxscore
        counts for games, stat-row counts for teams/players, game counts
        for seasons).

        The key= shape (Phase 2) resolves the natural key through the
        same crosswalk the matches section uses and returns `type`,
        `key`, `matches` (each hit: id, source, href, row_present,
        marked), `ambiguous` (more than one hit), `value` (the id when
        exactly one hit, else None), plus `marked`/`row_present` for the
        single-hit case. Teams key on {franchise, season} (franchise
        accepts a slug, abbreviation or full name), games on
        {home, away, date} plus optional score/season with an exact date
        match, players and people on {name} plus optional birthday
        (birthday required to be equal when given), season_info on
        {season}, and game_data reuses the game key.

        `marked=True, row_present=False` is a phantom; `marked=False,
        row_present=True` is the crash-window row with its mark lost.
        For game_data, `id` is interpreted as the Game_ID; for rankings,
        `row_present` is None because id_cache *is* its storage.
        """
        if key is not None:
            if href is not None or id is not None:
                raise ValueError("pass either key= or href=/id=, "
                                 "not both")
            return self._exists_key(type, key)
        if (href is None) == (id is None):
            raise ValueError("pass exactly one of href= or id=")
        known = set(ROW_TARGETS) | {"game_data", "rankings"}
        if type not in known:
            raise ValueError(
                f"unknown id_cache type {type!r}; expected one of "
                f"{', '.join(sorted(known))}")

        if type == "game_data":
            # The game_data mark's value is the flag 1, never an id, so an
            # id selector cannot query it directly: resolve the game's
            # href through its game_info mark first, then look the flag up
            # in that source column.
            return self._exists_game_data(id, href)

        if href is not None:
            marks = self._rows(
                "SELECT rowid AS rid, basketball_reference, nba, espn, "
                "value, type FROM id_cache WHERE type = ? AND "
                "(basketball_reference = ? OR nba = ? OR espn = ?)",
                (type, href, href, href))
        else:
            marks = self._rows(
                "SELECT rowid AS rid, basketball_reference, nba, espn, "
                "value, type FROM id_cache WHERE type = ? AND value = ?",
                (type, id))

        mark_list = []
        sources = {}
        for m in marks:
            col, m_href = self._mark_href(m)
            if col is not None:
                sources[col] = m_href
            mark_list.append({"source": col, "href": m_href,
                              "value": m["value"], "rowid": m["rid"]})

        value = marks[0]["value"] if marks else id
        result = {"type": type, "marked": bool(marks),
                  "row_present": None, "marks": mark_list,
                  "sources": sources, "value": value, "children": {}}

        if type in ROW_TARGETS:
            if value is None:
                result["row_present"] = None  # href never marked: unknown
            else:
                result["row_present"] = self._row_present(type, value)
            result["children"] = self._children(type, value, marks)
        else:  # rankings: id_cache is the storage, there is no row
            result["row_present"] = None
        return result

    def _exists_game_data(self, id, href):
        """exists() for game_data: `id` is the Game_ID, or pass the href."""
        marks = []
        game_id = id

        if href is not None:
            marks = self._rows(
                "SELECT rowid AS rid, basketball_reference, nba, espn, "
                "value, type FROM id_cache WHERE type = 'game_data' AND "
                "(basketball_reference = ? OR nba = ? OR espn = ?)",
                (href, href, href))
            game_id = self._game_id_for_href(*self._mark_href(marks[0])) \
                if marks else None
        elif id is not None:
            game = self._one(
                "SELECT rowid AS rid, basketball_reference, nba, espn, "
                "value, type FROM id_cache WHERE type = 'game_info' "
                "AND value = ?", (id,))
            if game is not None:
                col, game_href = self._mark_href(game)
                marks = self._rows(
                    "SELECT rowid AS rid, basketball_reference, nba, espn, "
                    "value, type FROM id_cache WHERE type = 'game_data' "
                    f"AND {col} = ?", (game_href,))

        mark_list = []
        sources = {}
        for m in marks:
            col, m_href = self._mark_href(m)
            if col is not None:
                sources[col] = m_href
            mark_list.append({"source": col, "href": m_href,
                              "value": m["value"], "rowid": m["rid"]})

        result = {"type": "game_data", "marked": bool(marks),
                  "row_present": None, "marks": mark_list,
                  "sources": sources, "value": game_id, "children": {}}
        if game_id is None:
            # An unresolvable href: nothing can be verified without the id.
            result["row_present"] = None
            return result
        children = self._box_children(game_id)
        children["game_id"] = game_id
        result["children"] = children
        result["row_present"] = any(children[t] for t in BOXTABLES)
        return result

    def _exists_key(self, type, key):
        """Natural-key exists(): resolve `key` to ids, then attribute them.

        Resolution goes through the same crosswalk the matches section
        uses (identity.py), so a team may be named by slug, abbreviation
        or full name, dates accept any format the sources store, and a
        player is found by normalized name. Everything is report-only.
        """
        if not isinstance(key, dict):
            raise ValueError("key= must be a dict of natural-key fields")
        known = set(ROW_TARGETS) | {"game_data"}
        if type not in known:
            raise ValueError(
                f"unknown id_cache type {type!r}; expected one of "
                f"{', '.join(sorted(known))}")

        ident = self._identity()

        if type == "game_data":
            game = self._exists_key("game_info", key)
            if game["value"] is not None:
                # One resolved game: report its real game_data marks and
                # boxscore children, keeping the key-shape extras.
                result = self._exists_game_data(game["value"], None)
                result["key"] = dict(key)
                result["matches"] = game["matches"]
                result["ambiguous"] = False
                return result
            return {"type": "game_data", "key": dict(key),
                    "matches": game["matches"],
                    "ambiguous": game["ambiguous"],
                    "value": None, "marked": None,
                    "row_present": game["row_present"]}

        if type == "season_info":
            season = key.get("season", key.get("Season"))
            if isinstance(season, bool) or not isinstance(season, int):
                raise ValueError("season_info key needs an integer "
                                 "'season'")
            ids = [season] if season in ident["rows"]["season_info"] else []
            return self._key_result(type, key, ids)

        if type == "team_info":
            if "franchise" not in key:
                raise ValueError("team_info key needs 'franchise' and "
                                 "'season'")
            slug = identity.alias_token(key["franchise"])
            if slug is None:
                raise ValueError(f"unknown team {key['franchise']!r}")
            season = key.get("season", key.get("Season"))
            if isinstance(season, bool) or not isinstance(season, int):
                raise ValueError("team_info key needs an integer 'season'")
            ids = [tid for tid, s in ident["team_slug"].items()
                   if s == slug and
                   ident["rows"]["team_info"][tid]["Season"] == season]
            return self._key_result(type, key, ids)

        if type == "game_info":
            missing = [f for f in ("home", "away", "date")
                       if f not in key]
            if missing:
                raise ValueError("game_info key needs " +
                                 ", ".join(missing))
            home = identity.alias_token(key["home"])
            if home is None:
                raise ValueError(f"unknown home team {key['home']!r}")
            away = identity.alias_token(key["away"])
            if away is None:
                raise ValueError(f"unknown away team {key['away']!r}")
            date = identity.normalize_date(key["date"])
            if date is None:
                raise ValueError(f"unparseable date {key['date']!r}")
            score = key.get("score")
            if isinstance(score, dict):
                score = (score.get("home"), score.get("away"))
            if score is not None and (
                    not isinstance(score, (tuple, list)) or
                    len(score) != 2 or
                    any(isinstance(x, bool) or not isinstance(x, int)
                        for x in score)):
                raise ValueError("score must be an (home, away) pair of "
                                 "ints")
            season = key.get("season", key.get("Season"))
            ids = []
            for gid, g in ident["games"].items():
                if (g["home"], g["away"], g["date"]) != (home, away, date):
                    continue  # exact date match by contract
                if score is not None and g["score"] != tuple(score):
                    continue
                if season is not None and g["season"] != season:
                    continue
                ids.append(gid)
            return self._key_result(type, key, ids)

        if type in ("player_info", "referee_info", "coach_info",
                    "executive_info"):
            if "name" not in key:
                raise ValueError(f"{type} key needs 'name'")
            name = identity.normalize_name(key["name"])
            if not name:
                raise ValueError(f"{type} key needs a non-empty 'name'")
            bday = None
            raw_bday = key.get("birthday", key.get("Birthday"))
            if raw_bday not in (None, ""):
                bday = identity.normalize_birthday(raw_bday)
                if bday is None:
                    raise ValueError(f"unparseable birthday {raw_bday!r}")
            ids = []
            for eid, row in ident["rows"][type].items():
                if identity.normalize_name(row["Name"]) != name:
                    continue
                if bday is not None and identity.normalize_birthday(
                        row["Birthday"]) != bday:
                    continue
                ids.append(eid)
            return self._key_result(type, key, ids)

        raise ValueError(f"no key resolution for {type!r}")

    def _key_result(self, type, key, ids):
        """Standard exists(key=) result from resolved ids."""
        ids = sorted(set(ids))
        matches = self._match_rows(type, ids)
        return {"type": type, "key": dict(key), "matches": matches,
                "ambiguous": len(ids) > 1,
                "value": ids[0] if len(ids) == 1 else None,
                "marked": matches[0]["marked"] if matches else None,
                "row_present": bool(matches)}

    def _match_rows(self, type, ids):
        """exists(key=) `matches` entries: attribution plus row presence."""
        table, pk = ROW_TARGETS[type]
        ident = self._identity()
        rows = ident["rows"].get(table, {})
        attrib = ident["attrib"].get(table, {})
        matches = []
        for i in ids:
            a = attrib.get(i, {"source": None, "href": None,
                               "marked": False})
            matches.append({"id": i, "source": a["source"],
                            "href": a["href"],
                            "row_present": i in rows,
                            "marked": a["marked"]})
        return matches

    def _children(self, type, value, marks):
        """Dependent row counts for one entity (shared with exists())."""
        if value is None:
            return {}
        if type in ("game_info", "game_data"):
            children = self._box_children(value)
            col, href = (self._mark_href(marks[0]) if marks
                         else (None, None))
            children["game_data_mark"] = self._game_data_mark(col, href)
            return children
        if type == "team_info":
            row = self._one(
                "SELECT COUNT(*) AS n FROM team_games WHERE Team_ID = ?",
                (value,))
            return {"team_games": row["n"]}
        if type == "player_info":
            pg = self._one(
                "SELECT COUNT(*) AS n FROM player_games WHERE Player_ID = ?",
                (value,))
            pq = self._one(
                "SELECT COUNT(*) AS n FROM player_quarters "
                "WHERE Player_ID = ?", (value,))
            return {"player_games": pg["n"], "player_quarters": pq["n"]}
        if type == "season_info":
            row = self._one(
                "SELECT COUNT(*) AS n FROM game_info WHERE Season = ?",
                (value,))
            games = self._one(
                "SELECT Games FROM season_info WHERE Season = ?",
                (value,))
            return {"game_info_games": row["n"],
                    "games_expected": None if games is None else games["Games"]}
        if type == "referee_info":
            row = self._one(
                "SELECT COUNT(*) AS n FROM game_info WHERE "
                "(Referee_ID1 = ? OR Referee_ID2 = ? OR Referee_ID3 = ?)",
                (value, value, value))
            return {"game_info": row["n"]}
        if type == "coach_info":
            row = self._one(
                "SELECT COUNT(*) AS n FROM team_info WHERE Coach_ID = ?",
                (value,))
            return {"team_info": row["n"]}
        if type == "executive_info":
            row = self._one(
                "SELECT COUNT(*) AS n FROM team_info WHERE Executive_ID = ?",
                (value,))
            return {"team_info": row["n"]}
        return {}

    # ---------- repair ----------

    def clear_phantoms(self):
        """Delete marks whose claimed data is absent. Guarded.

        Two kinds are deleted, each by id_cache rowid (data tables are
        never touched): a phantom mark whose id has no referencing rows,
        and a lying game_data mark whose game has zero boxscore rows.
        A phantom whose id still has referencing rows is skipped -- the
        next scrape would mint a new id, duplicate the entity and orphan
        those rows -- and lands in the returned `skipped` list so the CLI
        can report it as needing the Phase 3 merge.

        Returns {"deleted": [...], "skipped": [...]}.
        """
        deleted, skipped = [], []

        # Lying game_data marks first: clearing a phantom game mark below
        # must not leave a completion flag pointing at it.
        for h in self.holes():
            if h["kind"] != "lying_mark" or not h.get("clearable"):
                continue
            self.con.execute("DELETE FROM id_cache WHERE rowid = ?",
                             (h["rowid"],))
            deleted.append(h)
            log.info("cleared lying game_data mark for game %s "
                     "(no boxscore rows; will retry)", h["game_id"])

        for p in self.phantoms():
            if p["kind"] != "phantom":
                continue
            if not p["clearable"]:
                skipped.append(p)
                log.warning("not clearing %s mark value %s: %s "
                            "referencing row(s); needs the Phase 3 merge",
                            p["type"], p["value"], p["dependencies"])
                continue
            self.con.execute("DELETE FROM id_cache WHERE rowid = ?",
                             (p["rowid"],))
            deleted.append(p)
            log.info("cleared phantom %s mark value %s (row missing; "
                     "will retry)", p["type"], p["value"])

        self.con.commit()
        self._ident = None  # marks changed: rebuild identity on next use
        return {"deleted": deleted, "skipped": skipped}
