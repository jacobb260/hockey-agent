import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hopsworks
from config import settings
import pandas as pd



class AgentFunctions:

    def __init__(self) -> None:
       
        self.project = hopsworks.login(
            project=settings.HOPSWORKS_PROJECT,
            api_key_value=settings.HOPSWORKS_API_KEY,
            host = settings.HOPSWORKS_HOST
        )

        self.fs = self.project.get_feature_store()
        self.player_season_stats_fg = None
        

    def get_player_overview(self, player_name, season):
        if self.player_season_stats_fg is None:
            self.player_season_stats_fg = self.fs.get_feature_group(name='player_season_stats', version=1)

        data =self.player_season_stats_fg.filter((self.player_season_stats_fg.skater_full_name == player_name) &
                                                (self.player_season_stats_fg.season_id == season)).read()
        #json_str = data.to_json(orient="records")
        cols = [
            "skater_full_name",
            "season_id",
            "team_abbrevs",
            "games_played",
            "position_code",
            "goals",
            "assists",
            "points",
            "points_per_game",
            "shots",
            "shooting_pct",
            "plus_minus",
            "time_on_ice_per_game",
        ]
        
        return data.loc[:, cols].copy()
    
    def get_team_overview(self, teamName, season):
        """
        Hämtar alla tillgängliga stats för ett lag under en viss säsong.
        """
        teams_fg = self.fs.get_feature_group(name='teams', version=1)
        data = teams_fg.filter(
            (teams_fg.team_full_name == teamName) &
            (teams_fg.season_id == season)
        ).read()
        
        # De viktigaste kolumnerna för team overview
        key_cols = [
            "team_full_name",
            "season_id",
            "games_played",
            "wins",
            "losses",
            "ot_losses",
            "points",
            "goals_for",
            "goals_against",
            "power_play_pct",
            "penalty_kill_pct",
        ]
        
        # Filtrera bara de kolumner som finns i data
        available_cols = [col for col in key_cols if col in data.columns]
        
        return data.loc[:, available_cols].copy()

    def top_players(self, season, position=None, metric="points", n=10):
        if self.player_season_stats_fg is None:
            self.player_season_stats_fg = self.fs.get_feature_group(name='player_season_stats', version=1)
        data = self.player_season_stats_fg.filter((self.player_season_stats_fg.season_id == season)).read()

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
    def get_goalie(self, name, season):
        """
        Returns a goalie's stats for a given season.
        """
        if not hasattr(self, "goalies_fg") or self.goalies_fg is None:
            self.goalies_fg = self.fs.get_feature_group(
                name="goalies",
                version=1
            )

        data = (
            self.goalies_fg
            .filter(
                (self.goalies_fg.goalie_full_name == name) &
                (self.goalies_fg.season_id == season)
            )
            .read()
        )

        cols = [
            "goalie_full_name",
            "season_id",
            "games_played",
            "wins",
            "losses",
            "save_pct",
            "goals_against_average",
            "shots_against",
            "goals_against",
            "time_on_ice",
        ]

        cols = [c for c in cols if c in data.columns]

        return data.loc[:, cols].copy()

# Global instans som du kan importera överallt 
agentFunctions = AgentFunctions()

    


