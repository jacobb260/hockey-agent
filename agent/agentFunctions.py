import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hopsworks
from config import settings
import pandas as pd



class AgentFunctions:
    """
    Samlad konfiguration för projektet.
    Läser värden från miljövariabler (.env).
    """

    def __init__(self) -> None:
       
        self.project = hopsworks.login(
            project=settings.HOPSWORKS_PROJECT,
            api_key_value=settings.HOPSWORKS_API_KEY,
            host = settings.HOPSWORKS_HOST
        )

        self.fs = self.project.get_feature_store()
        

    def get_player_overview(self, player_name, season):
        player_season_stats_fg = self.fs.get_feature_group(name='player_season_stats', version=1)
        data = player_season_stats_fg.filter((player_season_stats_fg.skater_full_name == player_name) &
                                                (player_season_stats_fg.season_id == season)).read()
        #json_str = data.to_json(orient="records")
        return data
    
    def top_players(self, season, position=None, metric="points", n=10):
        player_season_stats_fg = self.fs.get_feature_group(name='player_season_stats', version=1)
        data = player_season_stats_fg.filter((player_season_stats_fg.season_id == season)).read()

        if position == "F":
            data = data[data["position_code"].isin(["C", "L", "R"])]
        elif position:
            data = data[data["position_code"] == position]
        data = data[data[metric].notna()]
        return (
            data.sort_values(metric, ascending=False)
                .head(n)
                [["skater_full_name", "position_code", metric, "games_played"]]
        )


# Global instans som du kan importera överallt 
agentFunctions = AgentFunctions()

    


