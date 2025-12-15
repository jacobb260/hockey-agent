import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hopsworks
from config import settings
import pandas as pd

project = hopsworks.login(
    project=settings.HOPSWORKS_PROJECT,
    api_key_value=settings.HOPSWORKS_API_KEY,
    host = settings.HOPSWORKS_HOST
)

fs = project.get_feature_store() 

def get_player_overview(player_name, season):
    player_season_stats_fg = fs.get_feature_group(name='player_season_stats', version=1)
    data = player_season_stats_fg.filter((player_season_stats_fg.skater_full_name == player_name) &
                                               (player_season_stats_fg.season_id == season)).read()
    json_str = data.to_json(orient="records")
    return json_str
    

print(get_player_overview("Jesper Fast", "20232024"))
