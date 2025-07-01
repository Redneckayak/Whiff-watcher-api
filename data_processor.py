import pandas as pd
from mlb_api import MLBDataFetcher

class WhiffWatchDataProcessor:
    """Builds pitcher-batter matchup DataFrame for Whiff Watcher"""

    def __init__(self):
        self.fetcher = MLBDataFetcher()

    def get_today_matchups(self) -> pd.DataFrame:
        matchups = []
        today_games = self.fetcher.get_todays_games(pd.Timestamp.today().date())

        for game in today_games:
            # Skip games without a probable pitcher
            for side in ['home', 'away']:
                pitcher = game.get(f'{side}_pitcher')
                if not pitcher:
                    continue

                pitcher_stats = self.fetcher.get_pitcher_stats(pitcher['id'])
                if pitcher_stats['batters_faced'] == 0:
                    continue

                team_id = self.fetcher.get_team_id_by_name(game[f'{ "away" if side == "home" else "home" }_team'])
                if not team_id:
                    continue

                batters = self.fetcher.get_team_roster(team_id)
                for batter in batters:
                    batter_stats = self.fetcher.get_batter_stats(batter['id'])
                    if batter_stats['at_bats'] == 0:
                        continue

                    matchup = {
                        'game_info': {
                            'home_team': game['home_team'],
                            'away_team': game['away_team'],
                            'game_time': game['game_time'],
                            'status': game['status']
                        },
                        'pitcher_name': pitcher['name'],
                        'pitcher_so_rate': pitcher_stats['so_rate'],
                        'pitcher_batters_faced': pitcher_stats['batters_faced'],
                        'batter_name': batter['name'],
                        'batter_so_rate': batter_stats['so_rate'],
                        'batter_at_bats': batter_stats['at_bats'],
                        'batter_strikeouts': batter_stats['strikeouts']
                    }
                    matchups.append(matchup)

        if not matchups:
            return pd.DataFrame()

        return pd.DataFrame(matchups)
