import pandas as pd
import numpy as np
from typing import Dict, List
from mlb_api import MLBDataFetcher  # Ensure mlb_api.py has this class

class StrikeoutPredictor:
    """Generates strikeout predictions based on pitcher-batter matchups"""

    def __init__(self):
        self.pitcher_weight = 0.6
        self.batter_weight = 0.4
        self.league_avg_pitcher_so = 15.0
        self.league_avg_batter_so = 22.0
        self.min_batter_ab = 150  # ✅ Minimum AB filter

    def predict_strikeouts(self, matchups_df: pd.DataFrame, threshold: float = 20.0) -> pd.DataFrame:
        if matchups_df.empty:
            return pd.DataFrame()

        # ✅ Filter out batters with fewer than 150 AB
        matchups_df = matchups_df[matchups_df['batter_at_bats'] >= self.min_batter_ab]

        # Keep only matchups with high strikeout potential
        high_rate_matchups = matchups_df[
            (matchups_df['pitcher_so_rate'] >= threshold) &
            (matchups_df['batter_so_rate'] >= threshold)
        ].copy()

        if high_rate_matchups.empty:
            return pd.DataFrame()

        high_rate_matchups['confidence_score'] = self._calculate_confidence_score(high_rate_matchups)
        high_rate_matchups['strikeout_probability'] = self._calculate_strikeout_probability(high_rate_matchups)

        high_rate_matchups = high_rate_matchups.sort_values('confidence_score', ascending=False)

        return high_rate_matchups[[
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

        confidence = np.minimum(
            (rate_confidence * 0.7 + sample_confidence * 0.3),
            1.0
        )
        confidence = np.maximum(confidence, 0.3)

        return confidence

    def _calculate_strikeout_probability(self, df: pd.DataFrame) -> pd.Series:
        pitcher_prob = df['pitcher_so_rate'] / 100.0
        batter_prob = df['batter_so_rate'] / 100.0
        combined_prob = self.pitcher_weight * pitcher_prob + self.batter_weight * batter_prob
        expected_abs = 3.5
        prob_no_strikeout = (1 - combined_prob) ** expected_abs
        return 1 - prob_no_strikeout

# ✅ This function is required by app.py
def generate_whiff_watch_data():
    fetcher = MLBDataFetcher()
    matchups_df = fetcher.get_today_matchups()

    predictor = StrikeoutPredictor()
    ranked_df = predictor.predict_strikeouts(matchups_df)

    if ranked_df.empty:
        return []

    result = ranked_df.to_dict(orient='records')
    return result
