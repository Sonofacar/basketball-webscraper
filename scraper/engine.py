# engine.py
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

from .backend_sources.basketball_reference import BasketballReferenceEngine
#from .backend_sources.nba import NBAEngine
#from .backend_sources.espn import ESPNEngine

from .backend_pagers.page_cacher import page

from .backend_databases.sqlite import sqlite
# from .backend_databases.mysql import mysql
# from .backend_databases.postgresql import postgresql

sourceEngines = {
        'basketball reference': BasketballReferenceEngine,
        # 'nba': NBAEngine,
        # 'espn': ESPNEngine,
}

baseURLs = {
        'basketball reference': "https://www.basketball-reference.com"
        # 'nba': "https://www.nba.com",
        # 'espn': "https://www.espn.com",
}

pagerEngines = {
        'native': page,
}

dbEngines = {
        'sqlite': sqlite,
        # 'mysql': mysql,
        # 'postgresql': postgresql,
}

def make_engine(name: str, pager: str, database, db_location = None, cache_size = 100):
    # Backend Engine defaults to Basketball-reference
    engine_class = sourceEngines.get(name.lower(), BasketballReferenceEngine)

    # Pager defaults to the native one
    page_engine = pagerEngines.get(pager.lower(), page)
    url = baseURLs.get(name.lower(), "https://www.basketball-reference.com")

    # Database defaults to sqlite
    db_engine = dbEngines.get(database.lower(), sqlite)

    engine = engine_class(page_engine(cache_size, url), db_engine(db_location))
    engine.get_id_cache()

    return engine
