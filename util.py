import datetime
import requests
import pandas as pd
import re
import time

def get_season(date):
    year = date.year
    month = date.month

    if month >= 10:
        next_year = year + 1
        season = str(year) + str(next_year)
        return season
    else:
        prev_year = year - 1
        season = str(prev_year) + str(year)
        return season
    
def fetch_games_from_nhl(season):
    """
    Hämtar alla matcher för en säsong från NHL REST API.
    """
    url = "https://api.nhle.com/stats/rest/en/game"

    params = {
        "cayenneExp": f"gameType=2 and season={season}"
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()["data"]
    return pd.DataFrame(data)

def fetch_teams():
    url = "https://api.nhle.com/stats/rest/en/team"
    response = requests.get(url)
    response.raise_for_status()

    teams = response.json()["data"]
    df = pd.DataFrame(teams)

    return df[[
        "id",
        "fullName",
        "franchiseId"
    ]]

def to_snake(name: str) -> str:
    # splitta CamelCase till snake_case
    s = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    return s.lower()


def fetch_player_form_for_season(season_id: str) -> pd.DataFrame:
    PLAYER_GAME_LOG_URL = "https://api.nhle.com/stats/rest/en/skater/summary"

    params = {
        "isGame": "true",  
        "cayenneExp": f"gameTypeId=2 and seasonId={season_id}",
        "limit": -1  
    }
    
    resp = requests.get(PLAYER_GAME_LOG_URL, params=params, timeout=20)
    resp.raise_for_status()
    
    data = resp.json()
    
    if "data" not in data or not data["data"]:
        return pd.DataFrame()
    
    df = pd.DataFrame(data["data"])
    
    # Säkerställ att seasonId finns
    if "seasonId" not in df.columns:
        df["seasonId"] = season_id
    
    return df

# URL för målvakter
GOALIE_GAME_LOG_URL = "https://api.nhle.com/stats/rest/en/goalie/summary"

def fetch_goalie_form_for_season(season_id: str) -> pd.DataFrame:
    params = {
        "isGame": "true",  
        "cayenneExp": f"gameTypeId=2 and seasonId={season_id}",
        "limit": -1  
    }
    
    resp = requests.get(GOALIE_GAME_LOG_URL, params=params, timeout=20)
    resp.raise_for_status()
    
    data = resp.json()
    
    if "data" not in data or not data["data"]:
        return pd.DataFrame()
    
    df = pd.DataFrame(data["data"])
    
    # Säkerställ att seasonId finns
    if "seasonId" not in df.columns:
        df["seasonId"] = season_id
    
    return df