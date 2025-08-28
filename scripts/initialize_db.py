# initialize.py
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

# Imports
import scraper
import argparse
import sys

desc = "Initialize database for scraping basketball data."
parser = argparse.ArgumentParser(prog = "bballInitializeDB",
                                 prefix_chars = "-",
                                 description = desc,
                                 epilog = "")
loc_help = """Location of database. File path for sqlite, otherwise, this should be the
url path to a server."""
parser.add_argument("-o",
                    "--location",
                    required = True,
                    help = loc_help)
type_help = "Type of connection. Must be one of sqlite, mysql, or postgresql."
parser.add_argument("-t",
                    "--type",
                    default = "sqlite",
                    choices = ["sqlite"],
                    # choices = ["sqlite", "mysql", "postgresql"],
                    help = type_help)
args = parser.parse_args(sys.argv[1:])

db_engine = scraper.dbEngines.get(args.type, scraper.sqlite)
db = db_engine(args.location)

# Write out commands to create tables
game_info = """CREATE TABLE IF NOT EXISTS game_info(
Home_Team_Name TEXT,
Away_Team_Name TEXT,
Date TEXT,
Location TEXT,
Duration INTEGER,
Attendance INTEGER CHECK (Attendance >= 0),
Game_ID INTEGER NOT NULL PRIMARY KEY,
Home_Team_ID INTEGER,
Away_Team_ID INTEGER,
Season INTEGER CHECK (Season > 1990),
Playoffs BOOLEAN NOT NULL CHECK (Playoffs IN (0, 1)),
In_Season_Tournament BOOLEAN NOT NULL CHECK (Playoffs IN (0, 1)),
Play_In BOOLEAN NOT NULL CHECK (Playoffs IN (0, 1)),
Referee_ID1 INTEGER,
Referee_ID2 INTEGER,
Referee_ID3 INTEGER,
FOREIGN KEY(Home_Team_ID) REFERENCES team_info(Team_ID),
FOREIGN KEY(Away_Team_ID) REFERENCES team_info(Team_ID),
FOREIGN KEY(Season) REFERENCES season_info(Season),
FOREIGN KEY(Referee_ID1) REFERENCES referees(Referee_ID),
FOREIGN KEY(Referee_ID2) REFERENCES referees(Referee_ID),
FOREIGN KEY(Referee_ID3) REFERENCES referees(Referee_ID)
);"""

team_info = """CREATE TABLE IF NOT EXISTS team_info(
Name TEXT,
Abbreviation TEXT,
Wins INTEGER NOT NULL CHECK (Wins >= 0),
Losses INTEGER NOT NULL CHECK (Losses >= 0),
Location TEXT,
Playoff_Appearance BOOLEAN NOT NULL CHECK (Playoff_Appearance IN (0, 1)),
League_Ranking INTEGER NOT NULL CHECK (League_Ranking > 0),
Team_ID INTEGER NOT NULL PRIMARY KEY,
Season INTEGER CHECK (Season > 1990),
Coach_ID INTEGER,
Executive_ID INTEGER,
FOREIGN KEY(Season) REFERENCES season_info(Season),
FOREIGN KEY(Executive_ID) REFERENCES executives(Executive_ID),
FOREIGN KEY(Coach_ID) REFERENCES coaches(Coach_ID)
);"""

team_games = """CREATE TABLE IF NOT EXISTS team_games(
Seconds INTEGER CHECK (Seconds >= 0),
Threes INTEGER NOT NULL DEFAULT 0 CHECK (Threes >= 0),
Three_Attempts INTEGER NOT NULL DEFAULT 0 CHECK (Three_Attempts >= 0),
Field_Goals INTEGER NOT NULL DEFAULT 0 CHECK (Field_Goals >= 0),
Field_Goal_Attempts INTEGER NOT NULL DEFAULT 0 CHECK (Field_Goal_Attempts >= 0),
Freethrows INTEGER NOT NULL DEFAULT 0 CHECK (Freethrows >= 0),
Freethrow_Attempts INTEGER NOT NULL DEFAULT 0 CHECK (Freethrow_Attempts >= 0),
Offensive_Rebounds INTEGER NOT NULL DEFAULT 0 CHECK (Offensive_Rebounds >= 0),
Defensive_Rebounds INTEGER NOT NULL DEFAULT 0 CHECK (Defensive_Rebounds >= 0),
Assists INTEGER NOT NULL DEFAULT 0 CHECK (Assists >= 0),
Steals INTEGER NOT NULL DEFAULT 0 CHECK (Steals >= 0),
Blocks INTEGER NOT NULL DEFAULT 0 CHECK (Blocks >= 0),
Turnovers INTEGER NOT NULL DEFAULT 0 CHECK (Turnovers >= 0),
Fouls INTEGER NOT NULL DEFAULT 0 CHECK (Fouls >= 0),
Points INTEGER NOT NULL DEFAULT 0 CHECK (Points >= 0),
Win BOOLEAN NOT NULL CHECK (Win IN (0, 1)),
Home BOOLEAN NOT NULL CHECK (Home IN (0, 1)),
Game_ID INTEGER,
Season INTEGER CHECK (Season > 1990),
Team_ID INTEGER,
Opponent_ID INTEGER,
FOREIGN KEY(Game_ID) REFERENCES game_info(Game_ID),
FOREIGN KEY(Season) REFERENCES season_info(Season),
FOREIGN KEY(Team_ID) REFERENCES team_info(Team_ID),
FOREIGN KEY(Opponent_ID) REFERENCES team_info(Team_ID)
);"""

team_quarters = """CREATE TABLE IF NOT EXISTS team_quarters(
Quarter INTEGER NOT NULL CHECK (Quarter > 0),
Seconds INTEGER CHECK (Seconds >= 0),
Threes INTEGER NOT NULL DEFAULT 0 CHECK (Threes >= 0),
Three_Attempts INTEGER NOT NULL DEFAULT 0 CHECK (Three_Attempts >= 0),
Field_Goals INTEGER NOT NULL DEFAULT 0 CHECK (Field_Goals >= 0),
Field_Goal_Attempts INTEGER NOT NULL DEFAULT 0 CHECK (Field_Goal_Attempts >= 0),
Freethrows INTEGER NOT NULL DEFAULT 0 CHECK (Freethrows >= 0),
Freethrow_Attempts INTEGER NOT NULL DEFAULT 0 CHECK (Freethrow_Attempts >= 0),
Offensive_Rebounds INTEGER NOT NULL DEFAULT 0 CHECK (Offensive_Rebounds >= 0),
Defensive_Rebounds INTEGER NOT NULL DEFAULT 0 CHECK (Defensive_Rebounds >= 0),
Assists INTEGER NOT NULL DEFAULT 0 CHECK (Assists >= 0),
Steals INTEGER NOT NULL DEFAULT 0 CHECK (Steals >= 0),
Blocks INTEGER NOT NULL DEFAULT 0 CHECK (Blocks >= 0),
Turnovers INTEGER NOT NULL DEFAULT 0 CHECK (Turnovers >= 0),
Fouls INTEGER NOT NULL DEFAULT 0 CHECK (Fouls >= 0),
Points INTEGER NOT NULL DEFAULT 0 CHECK (Points >= 0),
Win BOOLEAN NOT NULL CHECK (Win IN (0, 1)),
Home BOOLEAN NOT NULL CHECK (Home IN (0, 1)),
Game_ID INTEGER,
Season INTEGER CHECK (Season > 1990),
Team_ID INTEGER,
Opponent_ID INTEGER,
FOREIGN KEY(Game_ID) REFERENCES game_info(Game_ID),
FOREIGN KEY(Season) REFERENCES season_info(Season),
FOREIGN KEY(Team_ID) REFERENCES team_info(Team_ID),
FOREIGN KEY(Opponent_ID) REFERENCES team_info(Team_ID)
);"""

player_info = """CREATE TABLE IF NOT EXISTS player_info(
Name TEXT,
Shoots TEXT CHECK (Shoots LIKE "L" OR Shoots LIKE "R"),
Birthday TEXT,
High_School BOOLEAN NOT NULL CHECK (High_School IN (0, 1)),
College BOOLEAN NOT NULL CHECK (College IN (0, 1)),
Draft_Position INTEGER DEFAULT 0,
Draft_Team TEXT,
Draft_Year INTEGER DEFAULT 0,
Debut_Date TEXT,
Player_ID INTEGER NOT NULL PRIMARY KEY
);"""

player_games = """CREATE TABLE IF NOT EXISTS player_games(
Seconds INTEGER NOT NULL DEFAULT 0 CHECK (Seconds >= 0),
Threes INTEGER NOT NULL DEFAULT 0 CHECK (Threes >= 0),
Three_Attempts INTEGER NOT NULL DEFAULT 0 CHECK (Three_Attempts >= 0),
Field_Goals INTEGER NOT NULL DEFAULT 0 CHECK (Field_Goals >= 0),
Field_Goal_Attempts INTEGER NOT NULL DEFAULT 0 CHECK (Field_Goal_Attempts >= 0),
Freethrows INTEGER NOT NULL DEFAULT 0 CHECK (Freethrows >= 0),
Freethrow_Attempts INTEGER NOT NULL DEFAULT 0 CHECK (Freethrow_Attempts >= 0),
Offensive_Rebounds INTEGER NOT NULL DEFAULT 0 CHECK (Offensive_Rebounds >= 0),
Defensive_Rebounds INTEGER NOT NULL DEFAULT 0 CHECK (Defensive_Rebounds >= 0),
Assists INTEGER NOT NULL DEFAULT 0 CHECK (Assists >= 0),
Steals INTEGER NOT NULL DEFAULT 0 CHECK (Steals >= 0),
Blocks INTEGER NOT NULL DEFAULT 0 CHECK (Blocks >= 0),
Turnovers INTEGER NOT NULL DEFAULT 0 CHECK (Turnovers >= 0),
Fouls INTEGER NOT NULL DEFAULT 0 CHECK (Fouls >= 0),
Points INTEGER NOT NULL DEFAULT 0 CHECK (Points >= 0),
PM INTEGER NOT NULL DEFAULT 0,
Win BOOLEAN NOT NULL CHECK (Win IN (0, 1)),
Home BOOLEAN NOT NULL CHECK (Home IN (0, 1)),
Player_ID INTEGER,
Game_ID INTEGER,
Season INTEGER CHECK (Season > 1990),
Team_ID INTEGER,
Opponent_ID INTEGER,
FOREIGN KEY(Player_ID) REFERENCES player_info(Player_ID),
FOREIGN KEY(Game_ID) REFERENCES game_info(Game_ID),
FOREIGN KEY(Season) REFERENCES season_info(Season),
FOREIGN KEY(Team_ID) REFERENCES team_info(Team_ID),
FOREIGN KEY(Opponent_ID) REFERENCES team_info(Team_ID)
);"""

player_quarters = """CREATE TABLE IF NOT EXISTS player_quarters(
Quarter INTEGER NOT NULL CHECK (Quarter > 0),
Seconds INTEGER NOT NULL DEFAULT 0 CHECK (Seconds >= 0),
Threes INTEGER NOT NULL DEFAULT 0 CHECK (Threes >= 0),
Three_Attempts INTEGER NOT NULL DEFAULT 0 CHECK (Three_Attempts >= 0),
Field_Goals INTEGER NOT NULL DEFAULT 0 CHECK (Field_Goals >= 0),
Field_Goal_Attempts INTEGER NOT NULL DEFAULT 0 CHECK (Field_Goal_Attempts >= 0),
Freethrows INTEGER NOT NULL DEFAULT 0 CHECK (Freethrows >= 0),
Freethrow_Attempts INTEGER NOT NULL DEFAULT 0 CHECK (Freethrow_Attempts >= 0),
Offensive_Rebounds INTEGER NOT NULL DEFAULT 0 CHECK (Offensive_Rebounds >= 0),
Defensive_Rebounds INTEGER NOT NULL DEFAULT 0 CHECK (Defensive_Rebounds >= 0),
Assists INTEGER NOT NULL DEFAULT 0 CHECK (Assists >= 0),
Steals INTEGER NOT NULL DEFAULT 0 CHECK (Steals >= 0),
Blocks INTEGER NOT NULL DEFAULT 0 CHECK (Blocks >= 0),
Turnovers INTEGER NOT NULL DEFAULT 0 CHECK (Turnovers >= 0),
Fouls INTEGER NOT NULL DEFAULT 0 CHECK (Fouls >= 0),
Points INTEGER NOT NULL DEFAULT 0 CHECK (Points >= 0),
PM INTEGER NOT NULL DEFAULT 0,
Win BOOLEAN NOT NULL CHECK (Win IN (0, 1)),
Home BOOLEAN NOT NULL CHECK (Home IN (0, 1)),
Player_ID INTEGER,
Game_ID INTEGER,
Season INTEGER CHECK (Season > 1990),
Team_ID INTEGER,
Opponent_ID INTEGER,
FOREIGN KEY(Player_ID) REFERENCES player_info(Player_ID),
FOREIGN KEY(Game_ID) REFERENCES game_info(Game_ID),
FOREIGN KEY(Season) REFERENCES season_info(Season),
FOREIGN KEY(Team_ID) REFERENCES team_info(Team_ID),
FOREIGN KEY(Opponent_ID) REFERENCES team_info(Team_ID)
);"""

season_info = """CREATE TABLE IF NOT EXISTS season_info(
Season INTEGER NOT NULL CHECK (Season > 1990) PRIMARY KEY,
Games INTEGER,
Teams INTEGER,
Champion INTEGER,
Finals_MVP INTEGER,
MVP INTEGER,
DPOY INTEGER,
MIP INTEGER,
SixMOTY INTEGER,
ROTY INTEGER,
FOREIGN KEY(Champion) REFERENCES team_info(Team_ID),
FOREIGN KEY(Finals_MVP) REFERENCES player_info(Player_ID),
FOREIGN KEY(MVP) REFERENCES player_info(Player_ID),
FOREIGN KEY(DPOY) REFERENCES player_info(Player_ID),
FOREIGN KEY(MIP) REFERENCES player_info(Player_ID),
FOREIGN KEY(SixMOTY) REFERENCES player_info(Player_ID),
FOREIGN KEY(ROTY) REFERENCES player_info(Player_ID)
);"""

referee_info = """CREATE TABLE IF NOT EXISTS referee_info(
Name TEXT,
Number INTEGER,
Birthday TEXT,
Referee_ID INTEGER NOT NULL PRIMARY KEY
);"""

executive_info = """CREATE TABLE IF NOT EXISTS executive_info(
Name TEXT,
Birthday TEXT,
Executive_ID INTEGER NOT NULL PRIMARY KEY
);"""

coach_info = """CREATE TABLE IF NOT EXISTS coach_info(
Name TEXT,
Birthday TEXT,
Wins INTEGER NOT NULL CHECK (Wins >= 0),
Losses INTEGER NOT NULL CHECK (Losses >= 0),
Coach_ID INTEGER NOT NULL PRIMARY KEY
);"""

id_cache = """CREATE TABLE IF NOT EXISTS id_cache(
basketball_reference TEXT,
nba TEXT,
espn TEXT,
value INTEGER NOT NULL,
type TEXT,
CONSTRAINT unique_ids UNIQUE (basketball_reference,nba,espn,type)
);"""

# Execute Commands
def main():
    db.execute(game_info)
    db.execute(team_info)
    db.execute(team_games)
    db.execute(team_quarters)
    db.execute(player_info)
    db.execute(player_games)
    db.execute(player_quarters)
    db.execute(season_info)
    db.execute(referee_info)
    db.execute(executive_info)
    db.execute(coach_info)
    db.execute(id_cache)

if __name__ == "__main__":
    main()
