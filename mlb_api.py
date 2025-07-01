import requests
import json
from datetime import datetime, date
from typing import List, Dict, Optional

class MLBDataFetcher:
    """Handles all MLB API data fetching operations"""
    
    def __init__(self):
        self.base_url = "https://statsapi.mlb.com/api/v1"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'WhiffWatcher/1.0'
        })

    def get_todays_games(self, target_date: date) -> List[Dict]:
        date_str = target_date.strftime('%Y-%m-%d')
        try:
            schedule_url = f"{self.base_url}/schedule"
            params = {
                'sportId': 1,
                'date': date_str,
                'hydrate': 'team,linescore,probablePitcher,lineups'
            }
            response = self.session.get(schedule_url, params=params, timeout=10)
            response.raise_for_status()
            schedule_data = response.json()
            if not schedule_data.get('dates'):
                return []

            games = []
            for date_info in schedule_data['dates']:
                for game in date_info.get('games', []):
                    game_info = self._extract_game_info(game)
                    if game_info:
                        games.append(game_info)
            return games

        except Exception as e:
            print(f"Error fetching MLB games: {e}")
            return []

    def _extract_game_info(self, game: Dict) -> Optional[Dict]:
        try:
            game_id = game['gamePk']
            away_team = game['teams']['away']['team']['name']
            home_team = game['teams']['home']['team']['name']

            away_pitcher = None
            home_pitcher = None

            if 'probablePitcher' in game['teams']['away']:
                away_pitcher = {
                    'id': game['teams']['away']['probablePitcher']['id'],
                    'name': game['teams']['away']['probablePitcher']['fullName']
                }

            if 'probablePitcher' in game['teams']['home']:
                home_pitcher = {
                    'id': game['teams']['home']['probablePitcher']['id'],
                    'name': game['teams']['home']['probablePitcher']['fullName']
                }

            return {
                'game_id': game_id,
                'away_team': away_team,
                'home_team': home_team,
                'away_pitcher': away_pitcher,
                'home_pitcher': home_pitcher,
                'game_time': game.get('gameDate'),
                'status': game.get('status', {}).get('detailedState', 'Unknown')
            }

        except KeyError as e:
            print(f"Missing game field: {e}")
            return None

    def get_pitcher_stats(self, pitcher_id: int, season: int = None) -> Dict:
        if season is None:
            season = datetime.now().year
        for try_season in [season, season - 1]:
            try:
                stats_url = f"{self.base_url}/people/{pitcher_id}/stats"
                params = {'stats': 'season', 'group': 'pitching', 'season': try_season}
                response = self.session.get(stats_url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                if data.get('stats') and data['stats'][0].get('splits'):
                    stats = data['stats'][0]['splits'][0]['stat']
                    so = float(stats.get('strikeOuts', 0))
                    bf = float(stats.get('battersFaced', 0))
                    if bf > 0:
                        return {
                            'strikeouts': so,
                            'batters_faced': bf,
                            'so_rate': (so / bf) * 100,
                            'innings_pitched': float(stats.get('inningsPitched', 0)),
                            'era': float(stats.get('era', 0.0))
                        }
            except:
                continue
        return {'so_rate': 0.0, 'strikeouts': 0, 'batters_faced': 0}

    def get_batter_stats(self, batter_id: int, season: int = None) -> Dict:
        if season is None:
            season = datetime.now().year
        for try_season in [season, season - 1]:
            try:
                stats_url = f"{self.base_url}/people/{batter_id}/stats"
                params = {'stats': 'season', 'group': 'hitting', 'season': try_season}
                response = self.session.get(stats_url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                if data.get('stats') and data['stats'][0].get('splits'):
                    stats = data['stats'][0]['splits'][0]['stat']
                    so = float(stats.get('strikeOuts', 0))
                    ab = float(stats.get('atBats', 0))
                    if ab > 0:
                        return {
                            'strikeouts': so,
                            'at_bats': ab,
                            'so_rate': (so / ab) * 100,
                            'avg': float(stats.get('avg', 0.0)),
                            'ops': float(stats.get('ops', 0.0))
                        }
            except:
                continue
        return {'so_rate': 0.0, 'strikeouts': 0, 'at_bats': 0}

    def get_team_roster(self, team_id: int) -> List[Dict]:
        try:
            all_batters = {}
            for roster_type in ['active', 'fullSeason', '40Man']:
                try:
                    url = f"{self.base_url}/teams/{team_id}/roster"
                    params = {'rosterType': roster_type}
                    resp = self.session.get(url, params=params, timeout=10)
                    resp.raise_for_status()
                    data = resp.json()
                    for player in data.get('roster', []):
                        if player['position']['type'] != 'Pitcher':
                            pid = player['person']['id']
                            if pid not in all_batters:
                                all_batters[pid] = {
                                    'id': pid,
                                    'name': player['person']['fullName'],
                                    'position': player['position']['name']
                                }
                except Exception as e:
                    print(f"Roster error: {e}")
                    continue
            return list(all_batters.values())
        except Exception as e:
            print(f"Failed to get roster: {e}")
            return []

    def get_team_id_by_name(self, team_name: str) -> Optional[int]:
        try:
            teams_url = f"{self.base_url}/teams"
            response = self.session.get(teams_url, params={'sportId': 1}, timeout=10)
            response.raise_for_status()
            data = response.json()
            for team in data.get('teams', []):
                if team['name'] == team_name:
                    return team['id']
            return None
        except Exception as e:
            print(f"Failed to find team ID: {e}")
            return None

    def get_today_matchups(self) -> List[Dict]:
        """Fetch today’s MLB matchups including probable starting pitchers"""
        date_str = datetime.now().strftime("%Y-%m-%d")
        url = f"{self.base_url}/schedule?sportId=1&date={date_str}&hydrate=team,linescore,probablePitcher"
        response = self.session.get(url)
        data = response.json()

        matchups = []

        for date in data.get("dates", []):
            for game in date.get("games", []):
                matchup = {
                    "game_id": game.get("gamePk"),
                    "home_team": game["teams"]["home"]["team"]["name"],
                    "away_team": game["teams"]["away"]["team"]["name"],
                    "home_pitcher": self._get_pitcher_info(game["teams"]["home"].get("probablePitcher")),
                    "away_pitcher": self._get_pitcher_info(game["teams"]["away"].get("probablePitcher"))
                }
                matchups.append(matchup)

        return matchups

    def _get_pitcher_info(self, pitcher: Optional[Dict]) -> Optional[Dict]:
        if not pitcher:
            return None
        return {
            "id": pitcher.get("id"),
            "name": pitcher.get("fullName")
        }
