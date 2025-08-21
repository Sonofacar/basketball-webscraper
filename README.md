# Basketball Webscraper

A python package of a modular webscraper for NBA basketball data.

The package is built to be able to switch data sources, databases, and web clients.
Here is a list of what's supported:
- Sources:
	- [X] [Basketball-Reference](https://www.basketball-reference.com)
	- [ ] [NBA](https://www.nba.com)
	- [ ] [ESPN](https://www.espn.com)
- Databases:
	- [X] SQLite
	- [ ] MySQL/MariaDB
	- [ ] PostgreSQL
- Web Clients:
	- [X] Native (Python requests with configurable page caching)
	- [ ] SwarmScrape (Another project of mine which obscures bot traffic)

TODO:
- [ ] Add daily scrape script
- [ ] Decide what to do about injured players (include or not)
- [ ] Match IDs from various sources
- [ ] Implement alternate sources, databases, and web clients:
	- [ ] NBA source
	- [ ] ESPN source
	- [ ] MySQL/MariaDB
	- [ ] PostgreSQL
	- [ ] SwarmScrape
- [ ] Tests
