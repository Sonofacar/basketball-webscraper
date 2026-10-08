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

"""Existence and integrity checks: the library behind bballVerify.

Everything here is read-only against an already-scraped database until
`clear_phantoms` is called explicitly; the CLI owns all flag handling.
Scans are set-based SQL (no network, no source code), so they work on any
database regardless of which sources filled it.

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

import sqlite3

from .debug import get_logger

log = get_logger(__name__)

# The per-source id_cache columns. Hrefs are namespaced per source
# ("/espn/...", "/stats/...", "/leagues/..."), so a href search across all
# three columns cannot alias.
SOURCE_COLUMNS = ("basketball_reference", "nba", "espn")

# Report sections, in the order the CLI prints them.
SECTIONS = ("phantoms", "holes", "orphans", "invariants")

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

    # ---------- exists() API ----------

    def exists(self, type, href = None, id = None, key = None):
        """Is one entity marked, present, or both?

            exists(type, href = "/espn/event/401704628")
            exists(type, id = 17)

        Returns a dict: `marked` (an id_cache mark exists), `row_present`
        (the target table has the row), `marks` (each mark with its source
        column and href), `value` (the resolved id), and `children`
        (dependent row counts -- boxscore counts for games, stat-row
        counts for teams/players, game counts for seasons).

        `marked=True, row_present=False` is a phantom; `marked=False,
        row_present=True` is the crash-window row with its mark lost.
        For game_data, `id` is interpreted as the Game_ID; for rankings,
        `row_present` is None because id_cache *is* its storage. Natural
        key selectors ("TIM@LAL 2024-10-22") arrive in Phase 2.
        """
        if key is not None:
            raise NotImplementedError(
                "natural-key selectors arrive in Phase 2")
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
        return {"deleted": deleted, "skipped": skipped}
