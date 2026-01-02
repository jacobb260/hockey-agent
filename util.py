import requests
import pandas as pd
import re
from datetime import datetime, date, timedelta
import calendar

def generate_season_ids(start_year=2000):
    current_year = datetime.now().year

    season_ids = []
    for year in range(start_year, current_year+1):
        season_ids.append(f"{year}{year+1}")

    return season_ids


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

    start_year = int(season_id[:4]) 
    end_year = int(season_id[4:]) 

    season_start = date(start_year, 10, 1)
    season_end = date(end_year, 4, 30)
    all_months = []
    #Fetch per month in order to get all player stats. The max limit from the api is 10 000 datapoints
    current = season_start 
    while current <= season_end:
        last_day_of_month = calendar.monthrange(current.year, current.month)[1]
        month_end = date(current.year, current.month, last_day_of_month)

        range_end = min(month_end, season_end)

        params = {
            "isGame": "true",  
            "cayenneExp": (
            f"gameTypeId=2 and seasonId={season_id} "
            f"and gameDate>='{current.isoformat()}' and gameDate<='{range_end.isoformat()}'"),
            "limit": -1  
        }
        
        print(f"Downloading {current} to {range_end} for season {season_id}")
        resp = requests.get(PLAYER_GAME_LOG_URL, params=params, timeout=20)
        resp.raise_for_status()
        
        data = resp.json().get("data")

        if data:
            df_month = pd.DataFrame(data)
            print("Shape: " + str(df_month.shape))
            if "seasonId" not in df_month.columns:
                df_month["seasonId"] = int(season_id)
            all_months.append(df_month)
        
        current = range_end + timedelta(days=1)
    
    if not all_months:
        return pd.DataFrame()
    
    return pd.concat(all_months, ignore_index=True)


def fetch_goalie_form_for_season(season_id: str) -> pd.DataFrame:
    # URL för målvakter
    GOALIE_GAME_LOG_URL = "https://api.nhle.com/stats/rest/en/goalie/summary"
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

def fetch_player_stats(season_id: str) -> pd.DataFrame:
    PLAYER_GAME_LOG_URL = "https://api.nhle.com/stats/rest/en/skater/summary"
    cayenne = f"gameTypeId=2 and seasonId={season_id}"

    base_params = {
        "isAggregate": "false",
        "isGame": "false",
        "start": 0,
        "limit": -1,
        "cayenneExp": cayenne,
    }

    resp = requests.get(PLAYER_GAME_LOG_URL, params=base_params, timeout=20)
    resp.raise_for_status()
    data = resp.json()["data"]
    return pd.DataFrame(data)


def fetch_goalies_for_season(season_id: str) -> pd.DataFrame:
    GOALIE_URL = "https://api.nhle.com/stats/rest/en/goalie/summary"
    params = {
        "cayenneExp": f"gameTypeId=2 and seasonId={season_id}",
        "limit": -1
    }

    resp = requests.get(GOALIE_URL, params=params, timeout=20)
    resp.raise_for_status()

    data = resp.json()["data"]
    df = pd.DataFrame(data)

    df["seasonId"] = season_id  # säkerställ att den finns
    return df


def fetch_team_for_season(season_id: str) -> pd.DataFrame:
    URL = "https://api.nhle.com/stats/rest/en/team/summary"
    params = {
        "cayenneExp": f"gameTypeId=2 and seasonId={season_id}",
        "limit": -1
    }

    resp = requests.get(URL, params=params, timeout=20)
    resp.raise_for_status()

    data = resp.json()["data"]
    df = pd.DataFrame(data)

    df["seasonId"] = season_id  # säkerställ att den finns
    return df