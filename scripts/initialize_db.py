# Imports
import sqlite3
import os

# db.sql name given from command line
db_name = '../bball_db'

if os.path.isfile(db_name):
    os.remove(db_name)

conn = sqlite3.connect(db_name)
cur = conn.cursor()

# Write out commands to create tables
game_info = '''CREATE TABLE IF NOT EXISTS game_info(
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
FOREIGN KEY(Season) REFERENCES seasons(Season),
FOREIGN KEY(Referee_ID1) REFERENCES referees(Referee_ID),
FOREIGN KEY(Referee_ID2) REFERENCES referees(Referee_ID),
FOREIGN KEY(Referee_ID3) REFERENCES referees(Referee_ID)
);'''

team_info = '''CREATE TABLE IF NOT EXISTS team_info(
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
FOREIGN KEY(Season) REFERENCES seasons(Season),
FOREIGN KEY(Executive_ID) REFERENCES executives(Executive_ID),
FOREIGN KEY(Coach_ID) REFERENCES coaches(Coach_ID)
);'''

team_games = '''CREATE TABLE IF NOT EXISTS team_games(
Seconds INTEGER CHECK (Total_minutes >= 0),
Threes INTEGER NOT NULL DEFAULT 0 CHECK (Threes >= 0),
Three_Attempts INTEGER NOT NULL DEFAULT 0 CHECK (Three_Attempts >= 0),
Twos INTEGER NOT NULL DEFAULT 0 CHECK (Twos >= 0),
Two_Attempts INTEGER NOT NULL DEFAULT 0 CHECK (Two_Attempts >= 0),
Freethrows INTEGER NOT NULL DEFAULT 0 CHECK (Freethrows >= 0),
Freethrow_Attempts INTEGER NOT NULL DEFAULT 0 CHECK (Freethrow_Attempts >= 0),
Offensive_Rebounds INTEGER NOT NULL DEFAULT 0 CHECK (Offensive_Rebounds >= 0),
Deffensive_Rebounds INTEGER NOT NULL DEFAULT 0 CHECK (Deffensive_Rebounds >= 0),
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
FOREIGN KEY(Season) REFERENCES seasons(Season),
FOREIGN KEY(Team_ID) REFERENCES team_info(Team_ID),
FOREIGN KEY(Opponent_ID) REFERENCES team_info(Team_ID)
);'''

team_quarters = '''CREATE TABLE IF NOT EXISTS team_quarters(
Quarter INTEGER NOT NULL CHECK (Quarter > 0),
Seconds INTEGER CHECK (Total_Minutes >= 0),
Threes INTEGER NOT NULL DEFAULT 0 CHECK (Threes >= 0),
Three_Attempts INTEGER NOT NULL DEFAULT 0 CHECK (Three_Attempts >= 0),
Twos INTEGER NOT NULL DEFAULT 0 CHECK (Twos >= 0),
Two_Attempts INTEGER NOT NULL DEFAULT 0 CHECK (Two_Attempts >= 0),
Freethrows INTEGER NOT NULL DEFAULT 0 CHECK (Freethrows >= 0),
Freethrow_Attempts INTEGER NOT NULL DEFAULT 0 CHECK (Freethrow_Attempts >= 0),
Offensive_Rebounds INTEGER NOT NULL DEFAULT 0 CHECK (Offensive_Rebounds >= 0),
Deffensive_Rebounds INTEGER NOT NULL DEFAULT 0 CHECK (Deffensive_Rebounds >= 0),
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
FOREIGN KEY(Season) REFERENCES seasons(Season),
FOREIGN KEY(Team_ID) REFERENCES team_info(Team_ID),
FOREIGN KEY(Opponent_ID) REFERENCES team_info(Team_ID)
);'''

player_info = '''CREATE TABLE IF NOT EXISTS player_info(
Name TEXT,
Shoots TEXT CHECK (Shoots LIKE 'L' OR Shoots LIKE 'R'),
Birthday TEXT,
High_School BOOLEAN NOT NULL CHECK (High_School IN (0, 1)),
College BOOLEAN NOT NULL CHECK (College IN (0, 1)),
Draft_Position INTEGER DEFAULT 0,
Draft_Team TEXT,
Draft_Year INTEGER DEFAULT 0,
Debut_Date TEXT,
Career_Seasons INTEGER DEFAULT 0,
Teams TEXT,
Player_ID INTEGER NOT NULL PRIMARY KEY
);'''

player_games = '''CREATE TABLE IF NOT EXISTS player_games(
Seconds INTEGER NOT NULL DEFAULT 0 CHECK (Seconds >= 0),
Threes INTEGER NOT NULL DEFAULT 0 CHECK (Threes >= 0),
Three_Attempts INTEGER NOT NULL DEFAULT 0 CHECK (Three_Attempts >= 0),
Twos INTEGER NOT NULL DEFAULT 0 CHECK (Twos >= 0),
Two_Attempts INTEGER NOT NULL DEFAULT 0 CHECK (Two_Attempts >= 0),
Freethrows INTEGER NOT NULL DEFAULT 0 CHECK (Freethrows >= 0),
Freethrow_Attempts INTEGER NOT NULL DEFAULT 0 CHECK (Freethrow_Attempts >= 0),
Offensive_Rebounds INTEGER NOT NULL DEFAULT 0 CHECK (Offensive_Rebounds >= 0),
Deffensive_Rebounds INTEGER NOT NULL DEFAULT 0 CHECK (Deffensive_Rebounds >= 0),
Assists INTEGER NOT NULL DEFAULT 0 CHECK (Assists >= 0),
Steals INTEGER NOT NULL DEFAULT 0 CHECK (Steals >= 0),
Blocks INTEGER NOT NULL DEFAULT 0 CHECK (Blocks >= 0),
Turnovers INTEGER NOT NULL DEFAULT 0 CHECK (Turnovers >= 0),
Fouls INTEGER NOT NULL DEFAULT 0 CHECK (Fouls >= 0),
Points INTEGER NOT NULL DEFAULT 0 CHECK (Points >= 0),
PM INTEGER NOT NULL DEFAULT 0,
Win BOOLEAN NOT NULL CHECK (Win IN (0, 1)),
Home BOOLEAN NOT NULL CHECK (Home IN (0, 1)),
Injured BOOLEAN NOT NULL CHECK (Injured IN (0, 1)),
Player_ID INTEGER,
Game_ID INTEGER,
Season INTEGER CHECK (Season > 1990),
Team_ID INTEGER,
Opponent_ID INTEGER,
FOREIGN KEY(Player_ID) REFERENCES player_info(Player_ID),
FOREIGN KEY(Game_ID) REFERENCES game_info(Game_ID),
FOREIGN KEY(Season) REFERENCES seasons(Season),
FOREIGN KEY(Team_ID) REFERENCES team_info(Team_ID),
FOREIGN KEY(Opponent_ID) REFERENCES team_info(Team_ID)
);'''

player_quarters = '''CREATE TABLE IF NOT EXISTS player_quarters(
Quarter INTEGER NOT NULL CHECK (Quarter > 0),
Seconds INTEGER NOT NULL DEFAULT 0 CHECK (Seconds >= 0),
Threes INTEGER NOT NULL DEFAULT 0 CHECK (Threes >= 0),
Three_Attempts INTEGER NOT NULL DEFAULT 0 CHECK (Three_Attempts >= 0),
Twos INTEGER NOT NULL DEFAULT 0 CHECK (Twos >= 0),
Two_Attempts INTEGER NOT NULL DEFAULT 0 CHECK (Two_Attempts >= 0),
Freethrows INTEGER NOT NULL DEFAULT 0 CHECK (Freethrows >= 0),
Freethrow_Attempts INTEGER NOT NULL DEFAULT 0 CHECK (Freethrow_Attempts >= 0),
Offensive_Rebounds INTEGER NOT NULL DEFAULT 0 CHECK (Offensive_Rebounds >= 0),
Deffensive_Rebounds INTEGER NOT NULL DEFAULT 0 CHECK (Deffensive_Rebounds >= 0),
Assists INTEGER NOT NULL DEFAULT 0 CHECK (Assists >= 0),
Steals INTEGER NOT NULL DEFAULT 0 CHECK (Steals >= 0),
Blocks INTEGER NOT NULL DEFAULT 0 CHECK (Blocks >= 0),
Turnovers INTEGER NOT NULL DEFAULT 0 CHECK (Turnovers >= 0),
Fouls INTEGER NOT NULL DEFAULT 0 CHECK (Fouls >= 0),
Points INTEGER NOT NULL DEFAULT 0 CHECK (Points >= 0),
PM INTEGER NOT NULL DEFAULT 0,
Win BOOLEAN NOT NULL CHECK (Win IN (0, 1)),
Home BOOLEAN NOT NULL CHECK (Home IN (0, 1)),
Injured BOOLEAN NOT NULL CHECK (Injured IN (0, 1)),
Player_ID INTEGER,
Game_ID INTEGER,
Season INTEGER CHECK (Season > 1990),
Team_ID INTEGER,
Opponent_ID INTEGER,
FOREIGN KEY(Player_ID) REFERENCES player_info(Player_ID),
FOREIGN KEY(Game_ID) REFERENCES game_info(Game_ID),
FOREIGN KEY(Season) REFERENCES seasons(Season),
FOREIGN KEY(Team_ID) REFERENCES team_info(Team_ID),
FOREIGN KEY(Opponent_ID) REFERENCES team_info(Team_ID)
);'''

seasons = '''CREATE TABLE IF NOT EXISTS seasons(
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
);'''

referee_info = '''CREATE TABLE IF NOT EXISTS referee_info(
Name TEXT,
Number INTEGER,
Birthday TEXT,
Referee_ID INTEGER NOT NULL PRIMARY KEY
);'''

executive_info = '''CREATE TABLE IF NOT EXISTS executive_info(
Name TEXT,
Birthday TEXT,
Teams TEXT,
Executive_ID INTEGER NOT NULL PRIMARY KEY
);'''

coach_info = '''CREATE TABLE IF NOT EXISTS coach_info(
Name TEXT,
Birthday TEXT,
Wins INTEGER NOT NULL CHECK (Wins >= 0),
Losses INTEGER NOT NULL CHECK (Losses >= 0),
Teams TEXT,
Coach_ID INTEGER NOT NULL PRIMARY KEY
);'''

# Execute Commands
def main():
    cur.execute(game_info)
    cur.execute(playoff_game_info)
    cur.execute(team_info)
    cur.execute(team_games)
    cur.execute(team_quarters)
    cur.execute(player_info)
    cur.execute(player_games)
    cur.execute(player_quarters)
    cur.execute(seasons)
    cur.execute(referee_info)
    cur.execute(executive_info)
    cur.execute(coach_info)

if __name__ == "__main__":
    main()
