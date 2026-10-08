# backend_databases/sqlite.py
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

from .abstract import database, pass_none_location
from ..debug import get_logger
import sqlite3

log = get_logger(__name__)

class sqlite(database):
    @pass_none_location
    def execute(self, command):
        conn = sqlite3.connect(self.location)
        cur = conn.cursor()
        try:
            cur.execute(command)
            return True
        except sqlite3.IntegrityError as e:
            # A CHECK/UNIQUE/PK violation drops this row. Returning False
            # lets save_data -- and through it _save_and_mark -- skip the
            # id_cache completion mark, so the next run retries instead of
            # claiming a hole is complete forever. Anything else (missing
            # table, locked database) still propagates and crashes loudly.
            log.error("could not execute statement (%s): %s", e, command)
            return False
        finally:
            conn.commit()
        cur.close()
        conn.close()

    @pass_none_location
    def save_data(self, data, table, fill_defaults=False):
        col_string = ", ".join(data.keys())
        query_base = f"INSERT into {table} ({col_string}) VALUES "
        conflict = ""
        if fill_defaults:
            # season_info is the only table whose primary key (Season) is a
            # natural key shared across sources -- id_cache marks are
            # per-source, so a second source's plain INSERT would always
            # collide on the PK and (post mark-after-save) never mark. On
            # conflict, only cells still holding a default (0 or NULL, what
            # refresh_output pads every unset field to) are replaced: the
            # first writer wins per cell, later real data fills the blanks,
            # a stub source's row is a no-op that still earns its mark, and
            # a row whose mark was lost self-heals. Season itself (the
            # conflict target) is never set. Only get_season_info passes
            # this; any other table has no Season unique target and fails
            # loudly at execute.
            sets = ", ".join(
                f"{col} = CASE WHEN {table}.{col} IS NULL "
                f"OR {table}.{col} = 0 THEN excluded.{col} "
                f"ELSE {table}.{col} END"
                for col in data.keys() if col != "Season")
            conflict = f" ON CONFLICT(Season) DO UPDATE SET {sets}"
        rows = list(zip(*data.values()))
        if not rows:
            # Non-empty column lists that zip to nothing mean the value
            # lists had unequal lengths and zip truncated every row away --
            # the old silent total-loss path. Treat it as a failed save so
            # no completion mark is written.
            log.error("save_data(%s): no rows to write (column value lists "
                      "have unequal lengths?); nothing saved", table)
            return False
        saved = 0
        for row in rows:
            query = query_base + str(row) + conflict + ";"
            if self.execute(query):
                saved += 1
        return saved > 0

    @pass_none_location
    def get_data(self, table, cols = ["*"]):
        command = f"SELECT {','.join(cols)} from {table};"
        conn = sqlite3.connect(self.location)
        cur = conn.cursor()
        count = cur.execute(command)
        output = cur.fetchall()
        cur.close()
        conn.commit()
        conn.close()
        return output

    @pass_none_location
    def give_connection(self):
        return sqlite3.connect(self.location)
