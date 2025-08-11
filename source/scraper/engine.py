from .backends.basketball_reference import BasketballReferenceEngine
#from .backends.nba import NBAEngine
#from .backends.espn import ESPNEngine

Engines = {
        'basketball reference': BasketballReferenceEngine
        #'nba': NBAEngine
        #'espn': ESPNEngine
}

def get_engine(name: str):
    engine_class = Engines.get(name.lower())
    if not engine_class:
        raise ValueError(f"Engine '{name}' not supported.")
    return engine_class()
