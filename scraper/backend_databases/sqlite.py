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
