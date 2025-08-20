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
                    choices = ["native"],
                    help = client_help)
site_help = "The website to request from."
parser.add_argument("-s",
                    "--site",
                    default = "basketball reference",
                    choices = ["basketball reference"],
                    # choices = ["basketball reference", "espn", "nba"],
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
else:
    hrefs = []

def main():
    for href in hrefs:
        tmp = engine.get_season_info(href)

if __name__ == "__main__":
    main()
