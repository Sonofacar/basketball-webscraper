import scraper
from page_cacher import page

# Setup
engine = scraper.get_engine('basketball reference')
pager = page(50)

# Set up Team_info library
href = '/teams/VAN/2000.html'
t_info = engine.get_team_info(href, pager)
href = '/teams/BOS/2009.html'
t_info = engine.get_team_info(href, pager)
href = '/teams/UTA/2017.html'
t_info = engine.get_team_info(href, pager)
href = '/teams/PHI/2020.html'
t_info = engine.get_team_info(href, pager)

# Set up Player_info library
href = '/players/g/georgke01.html'
p_info = engine.get_player_info(href, pager)
href = '/players/c/conlemi01.html'
p_info = engine.get_player_info(href, pager)
href = '/players/g/gayru01.html'
p_info = engine.get_player_info(href, pager)
href = '/players/a/allenra02.html'
p_info = engine.get_player_info(href, pager)
href = '/players/d/doncilu01.html'
p_info = engine.get_player_info(href, pager)

# Set up Referee, Executive, and Coach library
href = '/referees/adairbr99r.html'
ref_info = engine.get_referee_info(href, pager)
href = '/referees/dalener99r.html'
ref_info = engine.get_referee_info(href, pager)
href = '/referees/kennebi99r.html'
ref_info = engine.get_referee_info(href, pager)
href = '/executives/horstjo01x.html'
exec_info = engine.get_executive_info(href, pager)
href = '/executives/kleimza99x.html'
exec_info = engine.get_executive_info(href, pager)
href = '/executives/aingeda01x.html'
exec_info = engine.get_executive_info(href, pager)
href = '/coaches/jenkita01c.html'
co_info = engine.get_coach_info(href, pager)
href = '/coaches/riverdo01c.html'
co_info = engine.get_coach_info(href, pager)
href = '/coaches/pruntjo01c.html'
co_info = engine.get_coach_info(href, pager)
href = '/coaches/griffad01c.html'
co_info = engine.get_coach_info(href, pager)
href = '/coaches/hardywi01c.html'
co_info = engine.get_coach_info(href, pager)

# Set up Season_info library
href = '/leagues/NBA_2020.html'
s_info = engine.get_season_info(href, pager)
href = '/leagues/NBA_2021.html'
s_info = engine.get_season_info(href, pager)
href = '/leagues/NBA_2022.html'
s_info = engine.get_season_info(href, pager)
href = '/leagues/NBA_2023.html'
s_info = engine.get_season_info(href, pager)

# Set up game library
href = '/boxscores/202403040LAL.html'
g_info = engine.get_game_info(href, pager)
href = '/boxscores/202204200MIL.html'
g_info = engine.get_game_info(href, pager)
href = '/boxscores/202206080BOS.html'
g_info = engine.get_game_info(href, pager)
href = '/boxscores/202312090LAL.html'
g_info = engine.get_game_info(href, pager)
href = '/boxscores/200411030LAC.html'
g_info = engine.get_game_info(href, pager)
href = '/boxscores/200310280PHI.html'
g_info = engine.get_game_info(href, pager)
href = '/boxscores/202110200NYK.html'
g_info = engine.get_game_info(href, pager)

# Set up game data
href = '/boxscores/202403040LAL.html'
g_data = engine.get_game_data(href, pager)
href = '/boxscores/202204200MIL.html'
g_data = engine.get_game_data(href, pager)
href = '/boxscores/202206080BOS.html'
g_data = engine.get_game_data(href, pager)
href = '/boxscores/202312090LAL.html'
g_data = engine.get_game_data(href, pager)
href = '/boxscores/200411030LAC.html'
g_data = engine.get_game_data(href, pager)
href = '/boxscores/200310280PHI.html'
g_data = engine.get_game_data(href, pager)
href = '/boxscores/202110200NYK.html'
g_data = engine.get_game_data(href, pager)
g_data.team_data
g_data.team_data_quarters
g_data.player_data
g_data.player_data_quarters
