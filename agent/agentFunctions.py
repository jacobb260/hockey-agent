import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hopsworks
from config import settings
import pandas as pd
from unidecode import unidecode



class AgentFunctions:

    def __init__(self) -> None:
       
        self.project = hopsworks.login(
            project=settings.HOPSWORKS_PROJECT,
            api_key_value=settings.HOPSWORKS_API_KEY,
            host = settings.HOPSWORKS_HOST
        )

        self.fs = self.project.get_feature_store()
        self.games_fg = None
        self.player_season_stats_fg = None
        

    def get_player_overview(self, player_name, season):
        if self.player_season_stats_fg is None:
            self.player_season_stats_fg = self.fs.get_feature_group(name='player_season_stats', version=1)
        
        player_name = unidecode(player_name) #replace åäö etc with aao 

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
        data_to_return = data.loc[:, cols].copy()
        data_to_return.columns = (data_to_return.columns.str.replace("_", " ", regex=False).str.title())       
        data_to_return = data_to_return.rename(columns={
            "Time On Ice Per Game": "Time On Ice Per Game (sec)",
        })

        if len(data_to_return) == 0: # Here's a case where the user probably searches for a goalie.
            print("Calling get goalie", player_name)
            return self.get_goalie(player_name, season)
            
        return data_to_return
    
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
        data_to_return = data.loc[:, available_cols].copy()
        data_to_return.columns = (data_to_return.columns.str.replace("_", " ", regex=False).str.title())  
        return data_to_return

    def top_players(self, season, position=None, metric="points", n=10):
        if self.player_season_stats_fg is None:
            self.player_season_stats_fg = self.fs.get_feature_group(name='player_season_stats', version=1)
        data = self.player_season_stats_fg.filter((self.player_season_stats_fg.season_id == season)).read()

        if position == "F":
            data = data[data["position_code"].isin(["C", "L", "R"])]
        elif position:
            data = data[data["position_code"] == position]
        data = data[data[metric].notna()]
        data = data.sort_values(metric, ascending=False).head(n)[["skater_full_name", "position_code", metric, "games_played"]]
        data.columns = (data.columns.str.replace("_", " ", regex=False).str.title())
        return data
    
    def top_goalies(self, season, metric="save_pct", n=10):
        """
        Returnerar topp n målvakter för en säsong baserat på valt metric.
        """
        if not hasattr(self, "goalies_fg") or self.goalies_fg is None:
            self.goalies_fg = self.fs.get_feature_group(
                name="goalies",
                version=1
            )

        data = self.goalies_fg.filter(
            self.goalies_fg.season_id == season
        ).read()

        # Ta bort rader utan värde i metric
        data = data[data[metric].notna()]

        # Sortera (lägre GAA är bättre, annars högre är bättre)
        ascending = True if metric == "goals_against_average" else False
        data = data.sort_values(metric, ascending=ascending).head(n)

        cols = [
            "goalie_full_name",
            "team_abbrevs",
            "games_played",
            metric
        ]
        cols = [c for c in cols if c in data.columns]

        data_to_return = data.loc[:, cols].copy()
        data_to_return.columns = (
            data_to_return.columns
            .str.replace("_", " ", regex=False)
            .str.title()
        )

        return data_to_return

    def top_teams(self, season, metric="points", n=10):
        """
        Returnerar topp n lag för en säsong baserat på valt metric.
        Exempel på metric: points, wins, goals_for, power_play_pct
        """
        teams_fg = self.fs.get_feature_group(
            name="teams",
            version=1
        )

        data = teams_fg.filter(
            teams_fg.season_id == season
        ).read()

        data = data[data[metric].notna()]
        data = data.sort_values(metric, ascending=False).head(n)

        cols = [
            "team_full_name",
            "games_played",
            metric
        ]
        cols = [c for c in cols if c in data.columns]

        data_to_return = data.loc[:, cols].copy()
        data_to_return.columns = (
            data_to_return.columns
            .str.replace("_", " ", regex=False)
            .str.title()
        )

        return data_to_return

    def get_team_form(self, team_name, season, n=5):
        """
        Returnerar:
        1) Ett lags form över de n senaste matcherna
        2) En tabell med matcherna (datum, motstånd, resultat)
        """
        # Hämta feature group på samma sätt som övriga funktioner
        games_fg = self.fs.get_feature_group(name="matches", version=1)
        
        data = games_fg.filter(
            ((games_fg.home_team_name == team_name) |
            (games_fg.away_team_name == team_name)) &
            (games_fg.season == season)
        ).read()

        # Konvertera datum och filtrera bort framtida matcher
        data["game_date"] = pd.to_datetime(data["game_date"])
        today = pd.Timestamp.now().normalize()  # Dagens datum utan tid
        data = data[data["game_date"] < today]  # Behåll bara matcher upp till idag
    
        # Sortera på datum och ta n senaste
        data["game_date"] = pd.to_datetime(data["game_date"])
        data = data.sort_values("game_date").tail(n)

        points = 0
        goals_for = 0
        goals_against = 0
        wins = 0
        losses = 0

        matches = []

        for _, row in data.iterrows():
            if row["home_team_name"] == team_name:
                gf = row["home_score"]
                ga = row["visiting_score"]
                opponent = row["away_team_name"]
                home_away = "Home"
            else:
                gf = row["visiting_score"]
                ga = row["home_score"]
                opponent = row["home_team_name"]
                home_away = "Away"

            goals_for += gf
            goals_against += ga

            if gf > ga:
                points += 2
                wins += 1
                result = "W"
            else:
                losses += 1
                result = "L"

            matches.append({
                "Date": row["game_date"].date(),
                "Opponent": opponent,
                "Home/Away": home_away,
                "Result": result,
                "Score": f"{gf}-{ga}"
            })

        summary = pd.DataFrame([{
            "Team": team_name,
            "Games": len(data),
            "Wins": wins,
            "Losses": losses,
            "Points": points,
            "Points Per Game": round(points / len(data), 2),
            "Goals For": goals_for,
            "Goals Against": goals_against,
            "Goal Diff": goals_for - goals_against
        }])

        matches_df = pd.DataFrame(matches)

        matches_df = matches_df.iloc[::-1] #Reverse it so it's correct order.
        return summary, matches_df

    def get_player_form(self, player_name, season, n=5):
        """
        Hämtar en spelares n senaste matcher med mål, assists, poäng etc.
        
        Args:
            player_name: Spelarens fullständiga namn
            season: Säsong i format YYYYYYYY (t.ex. "20232024")
            n: Antal senaste matcher att hämta (default: 5)
        
        Returns:
            DataFrame med matchstatistik
        """
        # Hämta feature group med per-match data
        if not hasattr(self, "player_game_log_fg") or self.player_game_log_fg is None:
            self.player_game_log_fg = self.fs.get_feature_group(
                name="players_form",
                version=1
            )
        player_name = unidecode(player_name) #replace åäö etc with aao
        # Filtrera på spelare och säsong
        data = self.player_game_log_fg.filter(
            (self.player_game_log_fg.skater_full_name == player_name) &
            (self.player_game_log_fg.season_id == season)
        ).read()

        # Konvertera game_date till datetime och filtrera upp till idag
        data["game_date"] = pd.to_datetime(data["game_date"])
        today = pd.Timestamp.now().normalize()
        data = data[data["game_date"] <= today]
        
        if data.empty:
            return pd.DataFrame({
                "Message": [f"No games played yet for {player_name} in season {season}"]
            })
        
        # Sortera på datum och ta n senaste
        data = data.sort_values("game_date", ascending=False).head(n)
        
        # Välj och formatera kolumner
        cols = [
            "game_date",
            "opponent_team_abbrev",
            "home_road",
            "goals",
            "assists",
            "points",
            "shots",
            "plus_minus",
            "time_on_ice_per_game",
            "pp_points",
            "ev_points"
        ]
        
        # Filtrera bara kolumner som finns
        available_cols = [col for col in cols if col in data.columns]
        data_to_return = data[available_cols].copy()
        
        # Formatera kolumnnamn
        data_to_return.columns = (
            data_to_return.columns
            .str.replace("_", " ", regex=False)
            .str.title()
        )
        
        # Specifika ombenämningar
        rename_dict = {
            "Time On Ice Per Game": "TOI",
            "Opponent Team Abbrev": "Opponent",
            "Home Road": "H/A",
            "Plus Minus": "+/-",
            "Pp Points": "PP Pts",
            "Ev Points": "EV Pts"
        }
        
        data_to_return = data_to_return.rename(columns=rename_dict)
        
        # Formatera datum till enbart datum (inte datetime)
        if "Game Date" in data_to_return.columns:
            data_to_return["Game Date"] = data_to_return["Game Date"].dt.date
        
        return data_to_return

    def get_goalie_form(self, goalie_name, season, n=5):
        """
        Hämtar en målvakts n senaste matcher med saves, GAA, save%, etc.
        
        Args:
            goalie_name: Målvaktens fullständiga namn
            season: Säsong i format YYYYYYYY (t.ex. "20232024")
            n: Antal senaste matcher att hämta (default: 5)
        
        Returns:
            DataFrame med matchstatistik
        """
        # Hämta feature group med per-match data
        if not hasattr(self, "goalie_game_log_fg") or self.goalie_game_log_fg is None:
            self.goalie_game_log_fg = self.fs.get_feature_group(
                name="goalies_form",
                version=1
            )
        gaolie_name = unidecode(goalie_name) #replace åäö etc with aao
        # Filtrera på målvakt och säsong
        data = self.goalie_game_log_fg.filter(
            (self.goalie_game_log_fg.goalie_full_name == goalie_name) &
            (self.goalie_game_log_fg.season_id == season)
        ).read()
                
        if data.empty:
            return pd.DataFrame({
                "Message": [f"No game data found for {goalie_name} in season {season}"]
            })
        
        # Konvertera game_date till datetime och filtrera upp till idag
        data["game_date"] = pd.to_datetime(data["game_date"])
        today = pd.Timestamp.now().normalize()
        data = data[data["game_date"] <= today]
        
        if data.empty:
            return pd.DataFrame({
                "Message": [f"No games played yet for {goalie_name} in season {season}"]
            })
        
        # Sortera på datum och ta n senaste
        data = data.sort_values("game_date", ascending=False).head(n)
        
        # Välj och formatera kolumner för målvakter
        cols = [
            "game_date",
            "opponent_team_abbrev",
            "home_road",
            "decision",  # W, L, OT
            "saves",
            "shots_against",
            "goals_against",
            "save_pct",
            "goals_against_average",
            "time_on_ice"
        ]
        
        # Filtrera bara kolumner som finns
        available_cols = [col for col in cols if col in data.columns]
        data_to_return = data[available_cols].copy()
        
        # Formatera kolumnnamn
        data_to_return.columns = (
            data_to_return.columns
            .str.replace("_", " ", regex=False)
            .str.title()
        )
        
        # Specifika ombenämningar
        rename_dict = {
            "Opponent Team Abbrev": "Opponent",
            "Home Road": "H/A",
            "Save Pct": "SV%",
            "Goals Against Average": "GAA",
            "Shots Against": "SA",
            "Goals Against": "GA",
            "Time On Ice": "TOI"
        }
        
        data_to_return = data_to_return.rename(columns=rename_dict)
        
        # Formatera datum till enbart datum (inte datetime)
        if "Game Date" in data_to_return.columns:
            data_to_return["Game Date"] = data_to_return["Game Date"].dt.date
        
        # Formatera SV% och GAA till 3 decimaler
        if "SV%" in data_to_return.columns:
            data_to_return["SV%"] = data_to_return["SV%"].round(3)
        if "GAA" in data_to_return.columns:
            data_to_return["GAA"] = data_to_return["GAA"].round(2)
        
        return data_to_return

    def get_goalie(self, name, season):
        """
        Returns a goalie's stats for a given season.
        """
        if not hasattr(self, "goalies_fg") or self.goalies_fg is None:
            self.goalies_fg = self.fs.get_feature_group(
                name="goalies",
                version=1
            )

        name = unidecode(name) #replace åäö etc with aao

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
            "team_abbrevs",
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

        data_to_return = data.loc[:, cols].copy()
        data_to_return.columns = (data_to_return.columns.str.replace("_", " ", regex=False).str.title()) 
        data_to_return = data_to_return.rename(columns={
            "Time On Ice": "Time On Ice (sec)",
        }) 
        return data_to_return

# Global instans som du kan importera överallt 
agentFunctions = AgentFunctions()

    


