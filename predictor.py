import pandas as pd
import numpy as np
from typing import Dict, List

class StrikeoutPredictor:
    """Generates strikeout predictions based on pitcher-batter matchups"""

    def __init__(self):
        self.pitcher_weight = 0.6
        self.batter_weight = 0.4
        self.league_avg_pitcher_so = 15.0
        self.league_avg_batter_so = 22.0

    def predict_strikeouts(self, matchups_df: pd.DataFrame, threshold: float = 20.0) -> pd.DataFrame:
        if matchups_df.empty:
            return pd.DataFrame()
        try:
            high_rate_matchups = matchups_df[
                (matchups_df['pitcher_so_rate'] >= threshold) &
                (matchups_df['batter_so_rate'] >= threshold)
            ].copy()

            if high_rate_matchups.empty:
                return pd.DataFrame()

            high_rate_matchups['confidence_score'] = self._calculate_confidence_score(high_rate_matchups)
            high_rate_matchups['strikeout_probability'] = self._calculate_strikeout_probability(high_rate_matchups)
            high_rate_matchups['prediction_reason'] = self._generate_prediction_reasons(high_rate_matchups)

            high_rate_matchups = high_rate_matchups.sort_values('confidence_score', ascending=False)

            return high_rate_matchups
        except Exception as e:
            print(f"[ERROR] Generating predictions: {e}")
            return pd.DataFrame()

    def _calculate_confidence_score(self, df: pd.DataFrame) -> pd.Series:
        try:
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
        except Exception as e:
            print(f"[WARNING] Calculating confidence scores: {e}")
            return pd.Series([0.5] * len(df))

    def _calculate_strikeout_probability(self, df: pd.DataFrame) -> pd.Series:
        try:
            pitcher_prob = df['pitcher_so_rate'] / 100.0
            batter_prob = df['batter_so_rate'] / 100.0

            combined_prob = (
                self.pitcher_weight * pitcher_prob +
                self.batter_weight * batter_prob
            )

            expected_abs = 3.5
            prob_no_strikeout = (1 - combined_prob) ** expected_abs
            prob_at_least_one = 1 - prob_no_strikeout

            return prob_at_least_one
        except Exception as e:
            print(f"[WARNING] Calculating strikeout probabilities: {e}")
            return pd.Series([0.5] * len(df))

    def _generate_prediction_reasons(self, df: pd.DataFrame) -> pd.Series:
        reasons = []

        for _, row in df.iterrows():
            reason_parts = []

            if row['pitcher_so_rate'] >= 30:
                reason_parts.append(f"{row['pitcher_name']} is an elite strikeout pitcher ({row['pitcher_so_rate']:.1f}%)")
            elif row['pitcher_so_rate'] >= 25:
                reason_parts.append(f"{row['pitcher_name']} has excellent strikeout rates ({row['pitcher_so_rate']:.1f}%)")
            else:
                reason_parts.append(f"{row['pitcher_name']} has above-average strikeout rates ({row['pitcher_so_rate']:.1f}%)")

            if row['batter_so_rate'] >= 30:
                reason_parts.append(f"{row['batter_name']} strikes out frequently ({row['batter_so_rate']:.1f}%)")
            elif row['batter_so_rate'] >= 25:
                reason_parts.append(f"{row['batter_name']} has high strikeout rates ({row['batter_so_rate']:.1f}%)")
            else:
                reason_parts.append(f"{row['batter_name']} strikes out above average ({row['batter_so_rate']:.1f}%)")

            reasons.append(" and ".join(reason_parts))

        return pd.Series(reasons)

    def get_prediction_summary(self, predictions_df: pd.DataFrame) -> Dict:
        if predictions_df.empty:
            return {
                'total_predictions': 0,
                'high_confidence': 0,
                'medium_confidence': 0,
                'low_confidence': 0,
                'avg_confidence': 0,
                'avg_strikeout_prob': 0
            }

        try:
            high_conf = len(predictions_df[predictions_df['confidence_score'] >= 0.7])
            medium_conf = len(predictions_df[
                (predictions_df['confidence_score'] >= 0.5) &
                (predictions_df['confidence_score'] < 0.7)
            ])
            low_conf = len(predictions_df[predictions_df['confidence_score'] < 0.5])

            return {
                'total_predictions': len(predictions_df),
                'high_confidence': high_conf,
                'medium_confidence': medium_conf,
                'low_confidence': low_conf,
                'avg_confidence': predictions_df['confidence_score'].mean(),
                'avg_strikeout_prob': predictions_df['strikeout_probability'].mean() if 'strikeout_probability' in predictions_df.columns else 0
            }

        except Exception as e:
            print(f"[WARNING] Generating prediction summary: {e}")
            return {'total_predictions': 0}

    def rank_predictions(self, predictions_df: pd.DataFrame) -> pd.DataFrame:
        if predictions_df.empty:
            return predictions_df

        try:
            df = predictions_df.copy()

            df['ranking_score'] = (
                df['confidence_score'] * 0.4 +
                (df['pitcher_so_rate'] / 100.0) * 0.3 +
                (df['batter_so_rate'] / 100.0) * 0.3
            )

            df['prediction_rank'] = df['ranking_score'].rank(ascending=False, method='dense').astype(int)

            return df.sort_values('ranking_score', ascending=False)

        except Exception as e:
            print(f"[WARNING] Ranking predictions: {e}")
            return predictions_df
