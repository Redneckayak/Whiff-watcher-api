import pandas as pd
from typing import List, Dict, Optional
import streamlit as st
from datetime import datetime

class DataProcessor:
    """Processes MLB data to create pitcher-batter matchups"""
    
    def __init__(self):
        pass
    
    def process_game_matchups(self, game: Dict, fetcher, min_at_bats: int = 200) -> List[Dict]:
        """Process a single game to create pitcher-batter matchups"""
        
        matchups = []
        
        try:
            # Get basic game info
            game_info = f"{game['away_team']} @ {game['home_team']}"
            
            # Process away team (pitcher vs home batters)
            if game['away_pitcher']:
                away_pitcher_matchups = self._create_pitcher_matchups(
                    game['away_pitcher'],
                    game['home_team'],
                    game_info,
                    fetcher,
                    is_away_pitcher=True,
                    min_at_bats=min_at_bats
                )
                matchups.extend(away_pitcher_matchups)
            
            # Process home team (pitcher vs away batters)
            if game['home_pitcher']:
                home_pitcher_matchups = self._create_pitcher_matchups(
                    game['home_pitcher'],
                    game['away_team'],
                    game_info,
                    fetcher,
                    is_away_pitcher=False,
                    min_at_bats=min_at_bats
                )
                matchups.extend(home_pitcher_matchups)
                
        except Exception as e:
            st.warning(f"Error processing game matchups: {str(e)}")
        
        return matchups
    
    def _create_pitcher_matchups(self, pitcher: Dict, opposing_team: str, 
                               game_info: str, fetcher, is_away_pitcher: bool, min_at_bats: int = 200) -> List[Dict]:
        """Create pitcher vs batter matchups for one side of the game"""
        
        matchups = []
        
        try:
            # Get pitcher stats
            pitcher_stats = fetcher.get_pitcher_stats(pitcher['id'])
            
            # Get opposing team roster
            team_id = fetcher.get_team_id_by_name(opposing_team)
            if not team_id:
                return matchups
            
            roster = fetcher.get_team_roster(team_id)
            
            # Use all available batters from the roster
            for batter in roster:
                batter_stats = fetcher.get_batter_stats(batter['id'])
                
                # Only include batters with at least min_at_bats for meaningful stats
                if batter_stats['at_bats'] >= min_at_bats:
                    matchup = {
                        'game_info': game_info,
                        'pitcher_name': pitcher['name'],
                        'pitcher_so_rate': pitcher_stats['so_rate'],
                        'batter_name': batter['name'],
                        'batter_so_rate': batter_stats['so_rate'],
                        'batter_strikeouts': batter_stats['strikeouts'],
                        'batter_at_bats': batter_stats['at_bats'],
                    }
                    matchups.append(matchup)
                
        except Exception as e:
            st.warning(f"Error creating pitcher matchups: {str(e)}")
        
        return matchups
    
    def filter_high_strikeout_matchups(self, matchups_df: pd.DataFrame, 
                                     threshold: float = 20.0) -> pd.DataFrame:
        """Filter matchups where both pitcher and batter have high strikeout rates"""
        
        if matchups_df.empty:
            return matchups_df
        
        try:
            # Filter for high strikeout rates
            filtered_df = matchups_df[
                (matchups_df['pitcher_so_rate'] >= threshold) & 
                (matchups_df['batter_so_rate'] >= threshold)
            ].copy()
            
            return filtered_df
            
        except Exception as e:
            st.error(f"Error filtering matchups: {str(e)}")
            return pd.DataFrame()
    
    def calculate_combined_metrics(self, matchups_df: pd.DataFrame) -> pd.DataFrame:
        """Calculate combined metrics for each matchup"""
        
        if matchups_df.empty:
            return matchups_df
        
        try:
            df = matchups_df.copy()
            
            # Combined strikeout rate (weighted average)
            df['combined_so_rate'] = (df['pitcher_so_rate'] + df['batter_so_rate']) / 2
            
            # Difference metric (how much above league average)
            # Assuming league average strikeout rates around 15% for pitchers and 22% for batters
            league_avg_pitcher = 15.0
            league_avg_batter = 22.0
            
            df['pitcher_above_avg'] = df['pitcher_so_rate'] - league_avg_pitcher
            df['batter_above_avg'] = df['batter_so_rate'] - league_avg_batter
            
            # Sample size weights (more confidence with more data)
            df['pitcher_sample_weight'] = self._calculate_sample_weight(df['pitcher_batters_faced'])
            df['batter_sample_weight'] = self._calculate_sample_weight(df['batter_at_bats'])
            
            return df
            
        except Exception as e:
            st.error(f"Error calculating combined metrics: {str(e)}")
            return matchups_df
    
    def _calculate_sample_weight(self, sample_sizes: pd.Series) -> pd.Series:
        """Calculate weight based on sample size"""
        
        # Use log scale for sample size weighting
        # More at-bats/batters faced = higher confidence
        weights = sample_sizes.apply(lambda x: min(1.0, x / 200.0) if x > 0 else 0.1)
        return weights
    
    def add_historical_context(self, matchups_df: pd.DataFrame) -> pd.DataFrame:
        """Add historical context to matchups"""
        
        if matchups_df.empty:
            return matchups_df
        
        try:
            df = matchups_df.copy()
            
            # Add percentile rankings
            df['pitcher_so_percentile'] = df['pitcher_so_rate'].rank(pct=True) * 100
            df['batter_so_percentile'] = df['batter_so_rate'].rank(pct=True) * 100
            
            # Add categorical ratings
            df['pitcher_rating'] = df['pitcher_so_rate'].apply(self._rate_pitcher_strikeouts)
            df['batter_rating'] = df['batter_so_rate'].apply(self._rate_batter_strikeouts)
            
            return df
            
        except Exception as e:
            st.warning(f"Error adding historical context: {str(e)}")
            return matchups_df
    
    def _rate_pitcher_strikeouts(self, so_rate: float) -> str:
        """Rate pitcher strikeout ability"""
        if so_rate >= 30:
            return "Elite"
        elif so_rate >= 25:
            return "Excellent"
        elif so_rate >= 20:
            return "Above Average"
        elif so_rate >= 15:
            return "Average"
        else:
            return "Below Average"
    
    def _rate_batter_strikeouts(self, so_rate: float) -> str:
        """Rate batter strikeout tendency"""
        if so_rate >= 30:
            return "Very High"
        elif so_rate >= 25:
            return "High"
        elif so_rate >= 20:
            return "Above Average"
        elif so_rate >= 15:
            return "Average"
        else:
            return "Low"
