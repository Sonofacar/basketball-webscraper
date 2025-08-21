# scrape_daily.py
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

import scraper
import argparse
import sys
from datetime import date

desc = "Webscrape basketball data by year"
parser = argparse.ArgumentParser(prog = "bballScrapeYearly",
                                 prefix_chars = "-",
                                 description = desc,
                                 epilog = "")

loc_help = """Location of database. File path for sqlite, otherwise, this should be the
url path to a server."""
parser.add_argument("-o",
                    "--location",
                    required = True,
                    help = loc_help)
db_help = "Type of database to store data in."
parser.add_argument("-d",
                    "--db",
                    default = "sqlite",
                    choices = ["sqlite"],
                    # choices = ["sqlite", "mysql", "postgresql"],
                    help = db_help)
client_help = "The client software used to make requests from the website."
parser.add_argument("-c",
                    "--client",
                    default = "native",
                    choices = ["native"],
                    help = client_help)
site_help = "The website to request from."
parser.add_argument("-s",
                    "--site",
                    default = "basketball reference",
                    choices = ["basketball reference"],
                    # choices = ["basketball reference", "espn", "nba"],
                    help = client_help)
date_help = "Date to pull from. Must be yyyy-mm-dd format."
parser.add_argument("-t",
                    "--date",
                    default = date.isoformat(date.today())
                    help = date_help)
years_help = "A set of seasons, denoted by the year they end in, to scrape data from."
parser.add_argument("years",
                    nargs = "*",
                    type = int,
                    help = years_help)
args = parser.parse_args(sys.argv[1:])

years = args.years
engine = scraper.make_engine(args.site, args.client, args.db, args.location)

d = date.fromisoformat(args.date)

if args.site == "basketball reference":
    params = {"year": d.year,
              "month": d.month,
              "day": d.day - 1}
    page = requests.get("https://www.basketball-reference.com/boxscores/", params)
    soup = BeautifulSoup(page.content, features = "lxml")
    games = soup.find_all("div", {"class": "game_summary"})
    hrefs = [x.find('p', {"class": "links"}).find('a').attrs['href'] for x in games]
else:
    hrefs = []

def main():
    for href in hrefs:
        tmp = engine.get_data(hrefs)

if __name__ == "__main__":
    main()
