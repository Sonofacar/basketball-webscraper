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
    def save_data(self, data, table):
        col_string = ", ".join(data.keys())
        query_base = f"INSERT into {table} ({col_string}) VALUES "
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
            query = query_base + str(row) + ";"
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
