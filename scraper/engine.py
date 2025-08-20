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
