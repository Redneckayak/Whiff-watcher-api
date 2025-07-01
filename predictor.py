import pandas as pd
import numpy as np
from typing import Dict, List
from mlb_api import MLBDataFetcher  # Ensure mlb_api.py has this class

class StrikeoutPredictor:
    def __init__(self):
        self.pitcher_weight = 0.6
        self.batter_weight = 0.4
        self.league_avg_pitcher_so = 15.0
        self.league_avg_batter_so = 22.0
        self.min_batter_ab = 150

    def predict_strikeouts(self, matchups_df: pd.DataFrame, threshold: float = 20.0) -> pd.DataFrame:
        if matchups_df.empty:
            return pd.DataFrame()

        matchups_df = matchups_df[matchups_df['batter_at_bats'] >= self.min_batter_ab]

        high_rate_matchups = matchups_df[
            (matchups_df['pitcher_so_rate'] >= threshold) &
            (matchups_df['batter_so_rate'] >= threshold)
        ].copy()

        if high_rate_matchups.empty:
            return pd.DataFrame()

        high_rate_matchups['confidence_score'] = self._calculate_confidence_score(high_rate_matchups)
        high_rate_matchups['strikeout_probability'] = self._calculate_strikeout_probability(high_rate_matchups)

        return high_rate_matchups.sort_values('confidence_score', ascending=False)[[
            'batter_name', 'batter_so_rate', 'pitcher_name', 'pitcher_so_rate',
            'confidence_score', 'strikeout_probability'
        ]]

    def _calculate_confidence_score(self, df: pd.DataFrame) -> pd.Series:
        pitcher_normalized = (df['pitcher_so_rate'] - self.league_avg_pitcher_so) / self.league_avg_pitcher_so
        batter_normalized = (df['batter_so_rate'] - self.league_avg_batter_so) / self.league_avg_batter_so

        pitcher_sample_factor = np.minimum(df['pitcher_batters_faced'] / 200.0, 1.0)
        batter_sample_factor = np.minimum(df['batter_at_bats'] / 300.0, 1.0)

        rate_confidence = (
            self.pitcher_weight * pitcher_normalized +
            self.batter_weight * batter_normalized
        )

        sample_confidence = (pitcher_sample_factor + batter_sample_factor) / 2

        confidence = np.minimum(rate_confidence * 0.7 + sample_confidence * 0.3, 1.0)
        return np.maximum(confidence, 0.3)

    def _calculate_strikeout_probability(self, df: pd.DataFrame) -> pd.Series:
        pitcher_prob = df['pitcher_so_rate'] / 100.0
        batter_prob = df['batter_so_rate'] / 100.0
        combined_prob = self.pitcher_weight * pitcher_prob + self.batter_weight * batter_prob
        expected_abs = 3.5
        prob_no_strikeout = (1 - combined_prob) ** expected_abs
        return 1 - prob_no_strikeout

# ✅ This replaces your broken version of generate_whiff_watch_data
def generate_whiff_watch_data():
    fetcher = MLBDataFetcher()
    matchups = fetcher.get_today_matchups()

    full_matchups = []

    for game in matchups:
        for side in ['home', 'away']:
            pitcher_info = game[f"{side}_pitcher"]
            if pitcher_info is None:
                continue

            pitcher_id = pitcher_info['id']
            pitcher_name = pitcher_info['name']
            pitcher_stats = fetcher.get_pitcher_stats(pitcher_id)
            if pitcher_stats['batters_faced'] == 0:
                continue

            team_name = game[f"{'away' if side == 'home' else 'home'}_team"]
            team_id = fetcher.get_team_id_by_name(team_name)
            if team_id is None:
                continue

            batters = fetcher.get_team_roster(team_id)
            for batter in batters:
                batter_id = batter['id']
                batter_name = batter['name']
                batter_stats = fetcher.get_batter_stats(batter_id)
                if batter_stats['at_bats'] == 0:
                    continue

                full_matchups.append({
                    "pitcher_name": pitcher_name,
                    "pitcher_so_rate": pitcher_stats['so_rate'],
                    "pitcher_batters_faced": pitcher_stats['batters_faced'],
                    "batter_name": batter_name,
                    "batter_so_rate": batter_stats['so_rate'],
                    "batter_at_bats": batter_stats['at_bats']
                })

    df = pd.DataFrame(full_matchups)
    if df.empty:
        return []

    predictor = StrikeoutPredictor()
    ranked = predictor.predict_strikeouts(df)

    return ranked.to_dict(orient="records") if not ranked.empty else []
