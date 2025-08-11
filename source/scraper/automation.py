from .engine import get_engine
from page_cacher import page

#def get_id(t):

#def save_data(data, t):

def linker(t, href, pager) -> dict:
    soup = pager.get(href)
    engine = get_engine('basketball reference')

    match t:
        case 'referee':
            obj = engine.referee_info(soup)
            prev = get_id(t)
            obj.fetch(prev)
            data = obj.output()
            save_data(data, t)

        case 'executive':
            obj = engine.executive_info(soup)
            prev = get_id(t)
            obj.fetch(prev)
            data = obj.output()
            save_data(data, t)

        case 'coach':
            obj = engine.coach_info(soup)
            prev = get_id(t)
            obj.fetch(prev)
            data = obj.output()
            save_data(data, t)

        case 'player':
            obj = engine.player_info(soup)
            prev = get_id(t)
            obj.fetch(prev)
            data = obj.output()
            save_data(data, t)

        case 'team':
            obj = engine.team_info(soup)
            prev = get_id(t)
            obj.fetch(prev)
            data = obj.output()
            save_data(data, t)

        case 'game':
            obj = engine.game_info(soup)
            prev = get_id(t)
            obj.fetch(prev)
            data = obj.output()
            save_data(data, t)

        case 'game-data':
            obj = engine.game_data(soup)
            prev = get_id(t)
            obj.fetch(prev)
            data = obj.output()
            save_data(data, t)
            return # No ID is needed

        case 'season':
            obj = engine.season_info(soup)
            prev = get_id(t)
            obj.fetch(prev)
            data = obj.output()
            save_data(data, t)

    return obj.id
