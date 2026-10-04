# scrape_yearly.py
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
                    choices = ["native", "nba", "espn"],
                    help = client_help)
site_help = "The website to request from."
parser.add_argument("-s",
                    "--site",
                    default = "basketball reference",
                    choices = ["basketball reference", "nba", "espn"],
                    help = client_help)
years_help = "A set of seasons, denoted by the year they end in, to scrape data from."
parser.add_argument("years",
                    nargs = "*",
                    type = int,
                    help = years_help)
args = parser.parse_args(sys.argv[1:])

years = args.years
engine = scraper.make_engine(args.site, args.client, args.db, args.location)

if args.site == "basketball reference":
    hrefs = ["/leagues/NBA_" + str(x) + ".html" for x in years]
elif args.site == "nba":
    hrefs = ["/stats/teams/boxscores?Season=" + str(x - 1) + "-" + str(x)[2:] for x in years]
elif args.site == "espn":
    # ESPN has no season landing page; the year is the only thing the source
    # needs, and it reads the schedule and standings from the JSON APIs.
    hrefs = ["/espn/season/" + str(x) for x in years]
else:
    hrefs = []

def main():
    for href in hrefs:
        tmp = engine.get_season_info(href)

if __name__ == "__main__":
    main()
