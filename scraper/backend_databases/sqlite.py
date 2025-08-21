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
import sqlite3

class sqlite(database):
    @pass_none_location
    def execute(self, command):
        conn = sqlite3.connect(self.location)
        cur = conn.cursor()
        try:
            count = cur.execute(command)
        except sqlite3.IntegrityError as e:
            print(e)
        finally:
            conn.commit()
        cur.close()
        conn.close()

    @pass_none_location
    def save_data(self, data, table):
        col_string = ", ".join(data.keys())
        query_base = f"INSERT into {table} ({col_string}) VALUES "
        for row in zip(*data.values()):
            query = query_base + str(row) + ";"
            self.execute(query)

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
