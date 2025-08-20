import scraper
engine = scraper.make_engine("basketball reference", "native", "sqlite")
engine = scraper.make_engine("basketball reference", "native", "sqlite", "test.sql")

# Set up Team_info library
href = "/teams/VAN/2000.html"
t_info = engine.get_team_info(href)
href = "/teams/BOS/2009.html"
t_info = engine.get_team_info(href)
href = "/teams/UTA/2017.html"
t_info = engine.get_team_info(href)
href = "/teams/PHI/2020.html"
t_info = engine.get_team_info(href)

# Set up Player_info library
href = "/players/g/georgke01.html"
p_info = engine.get_player_info(href)
href = "/players/c/conlemi01.html"
p_info = engine.get_player_info(href)
href = "/players/g/gayru01.html"
p_info = engine.get_player_info(href)
href = "/players/a/allenra02.html"
p_info = engine.get_player_info(href)
href = "/players/d/doncilu01.html"
p_info = engine.get_player_info(href)

# Set up Referee, Executive, and Coach library
href = "/referees/adairbr99r.html"
ref_info = engine.get_referee_info(href)
href = "/referees/dalener99r.html"
ref_info = engine.get_referee_info(href)
href = "/referees/kennebi99r.html"
ref_info = engine.get_referee_info(href)
href = "/executives/horstjo01x.html"
exec_info = engine.get_executive_info(href)
href = "/executives/kleimza99x.html"
exec_info = engine.get_executive_info(href)
href = "/executives/aingeda01x.html"
exec_info = engine.get_executive_info(href)
href = "/coaches/jenkita01c.html"
co_info = engine.get_coach_info(href)
href = "/coaches/riverdo01c.html"
co_info = engine.get_coach_info(href)
href = "/coaches/pruntjo01c.html"
co_info = engine.get_coach_info(href)
href = "/coaches/griffad01c.html"
co_info = engine.get_coach_info(href)
href = "/coaches/hardywi01c.html"
co_info = engine.get_coach_info(href)

# Set up Season_info library
href = "/leagues/NBA_2020.html"
s_info = engine.get_season_info(href)
href = "/leagues/NBA_2021.html"
s_info = engine.get_season_info(href)
href = "/leagues/NBA_2022.html"
s_info = engine.get_season_info(href)
href = "/leagues/NBA_2023.html"
s_info = engine.get_season_info(href)

# Set up game library
href = "/boxscores/202403040LAL.html"
g_info = engine.get_game_info(href)
href = "/boxscores/202204200MIL.html"
g_info = engine.get_game_info(href)
href = "/boxscores/202206080BOS.html"
g_info = engine.get_game_info(href)
href = "/boxscores/202312090LAL.html"
g_info = engine.get_game_info(href)
href = "/boxscores/200411030LAC.html"
g_info = engine.get_game_info(href)
href = "/boxscores/200310280PHI.html"
g_info = engine.get_game_info(href)
href = "/boxscores/202110200NYK.html"
g_info = engine.get_game_info(href)

# Set up game data
href = "/boxscores/202403040LAL.html"
g_data = engine.get_game_data(href)
href = "/boxscores/202204200MIL.html"
g_data = engine.get_game_data(href)
href = "/boxscores/202206080BOS.html"
g_data = engine.get_game_data(href)
href = "/boxscores/202312090LAL.html"
g_data = engine.get_game_data(href)
href = "/boxscores/200411030LAC.html"
g_data = engine.get_game_data(href)
href = "/boxscores/200310280PHI.html"
g_data = engine.get_game_data(href)
href = "/boxscores/202110200NYK.html"
g_data = engine.get_game_data(href)
g_data.team_data
g_data.team_data_quarters
g_data.player_data
g_data.player_data_quarters
