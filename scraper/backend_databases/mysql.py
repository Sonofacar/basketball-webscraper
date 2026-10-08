# backend_databases/mysql.py
#
# Copyright (C) 2026 Carson Buttars
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
import mysql

class mysql(database):
    def __init__(self, user, password, database, host, port = 3306):
        self.user = user
        self.password = password
        self.database = database
        self.host = host
        self.port = port

    @pass_none_location
    def execute(self, command):
        conn = self.give_connection()
        cur = conn.cursor()
        try:
            count = cur.execute(command)
        # except: mariadb as e:
        #     print(e)
        finally:
            conn.commit()
        cur.close()
        conn.close()

    @pass_none_location
    def save_data(self, data, table, fill_defaults = False):
        col_string = ", ".join(data.keys())
        query_base = f"INSERT into {table} ({col_string}) VALUES "
        for row in zip(*data.values()):
            query = query_base + str(row) + ";"
            self.execute(query)

    @pass_none_location
    def get_data(self, table, cols = ["*"]):
        command = f"SELECT {','.join(cols)} from {table};"
        conn = self.give_connection()
        cur = conn.cursor()
        try:
            count = cur.execute(command)
            output = cur.fetchall()
        # except: mariadb as e:
        #     print(e)
        finally:
            conn.commit()
        cur.close()
        conn.close()
        return output

    @pass_none_location
    def give_connection(self):
        try:
            conn = mariadb.connect(
                user = self.user,
                password = self.password,
                host = self.host,
                port = self.port,
                database = self.database,
                connect_timeout = 10,
                autocommit = False,
                charset = "utf8mb4",
            )
            return conn
        # except mariadb.Error as e:
        #     print(f"Error connecting: {e}")
        #     raise
        except:
            raise
