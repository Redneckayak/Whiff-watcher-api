import requests
from datetime import datetime, date
from typing import List, Dict, Optional

class MLBDataFetcher:
    def __init__(self):
        self.base_url = "https://statsapi.mlb.com/api/v1"
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'WhiffWatcher/1.0'})

    def get_todays_games(self, target_date: date) -> List[Dict]:
        date_str = target_date.strftime('%Y-%m-%d')
        try:
            url = f"{self.base_url}/schedule"
            params = {
                'sportId': 1,
                'date': date_str,
                'hydrate': 'team,linescore,probablePitcher,lineups'
            }
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            games = []
            for date_info in data.get('dates', []):
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
            return {
                'game_id': game['gamePk'],
                'away_team': game['teams']['away']['team']['name'],
                'home_team': game['teams']['home']['team']['name'],
                'away_pitcher': self._get_pitcher_info(game['teams']['away'].get('probablePitcher')),
                'home_pitcher': self._get_pitcher_info(game['teams']['home'].get('probablePitcher')),
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
                url = f"{self.base_url}/people/{pitcher_id}/stats"
                params = {'stats': 'season', 'group': 'pitching', 'season': try_season}
                response = self.session.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                splits = data.get('stats', [{}])[0].get('splits', [])
                if splits:
                    stat = splits[0]['stat']
                    so = float(stat.get('strikeOuts', 0))
                    bf = float(stat.get('battersFaced', 0))
                    if bf > 0:
                        return {
                            'strikeouts': so,
                            'batters_faced': bf,
                            'so_rate': (so / bf) * 100,
                            'innings_pitched': float(stat.get('inningsPitched', 0)),
                            'era': float(stat.get('era', 0.0))
                        }
            except Exception:
                continue
        return {'so_rate': 0.0, 'strikeouts': 0, 'batters_faced': 0}

    def get_batter_stats(self, batter_id: int, season: int = None) -> Dict:
        if season is None:
            season = datetime.now().year
        for try_season in [season, season - 1]:
            try:
                url = f"{self.base_url}/people/{batter_id}/stats"
                params = {'stats': 'season', 'group': 'hitting', 'season': try_season}
                response = self.session.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                splits = data.get('stats', [{}])[0].get('splits', [])
                if splits:
                    stat = splits[0]['stat']
                    so = float(stat.get('strikeOuts', 0))
                    ab = float(stat.get('atBats', 0))
                    if ab > 0:
                        return {
                            'strikeouts': so,
                            'at_bats': ab,
                            'so_rate': (so / ab) * 100,
                            'avg': float(stat.get('avg', 0.0)),
                            'ops': float(stat.get('ops', 0.0))
                        }
            except Exception:
                continue
        return {'so_rate': 0.0, 'strikeouts': 0, 'at_bats': 0}

    def get_team_roster(self, team_id: int) -> List[Dict]:
        batters = {}
        for roster_type in ['active', 'fullSeason', '40Man']:
            try:
                url = f"{self.base_url}/teams/{team_id}/roster"
                params = {'rosterType': roster_type}
                response = self.session.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                for player in data.get('roster', []):
                    if player['position']['type'] != 'Pitcher':
                        pid = player['person']['id']
                        if pid not in batters:
                            batters[pid] = {
                                'id': pid,
                                'name': player['person']['fullName'],
                                'position': player['position']['name']
                            }
            except Exception:
                continue
        return list(batters.values())

    def get_team_id_by_name(self, team_name: str) -> Optional[int]:
        try:
            url = f"{self.base_url}/teams"
            response = self.session.get(url, params={'sportId': 1}, timeout=10)
            response.raise_for_status()
            data = response.json()
            for team in data.get('teams', []):
                if team['name'] == team_name:
                    return team['id']
        except Exception as e:
            print(f"Failed to find team ID: {e}")
        return None

    def get_today_matchups(self) -> List[Dict]:
        date_str = datetime.now().strftime("%Y-%m-%d")
        url = f"{self.base_url}/schedule?sportId=1&date={date_str}&hydrate=team,linescore,probablePitcher"
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            matchups = []
            for date_info in data.get("dates", []):
                for game in date_info.get("games", []):
                    matchups.append({
                        "game_id": game.get("gamePk"),
                        "home_team": game["teams"]["home"]["team"]["name"],
                        "away_team": game["teams"]["away"]["team"]["name"],
                        "home_pitcher": self._get_pitcher_info(game["teams"]["home"].get("probablePitcher")),
                        "away_pitcher": self._get_pitcher_info(game["teams"]["away"].get("probablePitcher"))
                    })
            return matchups
        except Exception as e:
            print(f"Failed to fetch matchups: {e}")
            return []

    def _get_pitcher_info(self, pitcher: Optional[Dict]) -> Optional[Dict]:
        if pitcher:
            return {"id": pitcher.get("id"), "name": pitcher.get("fullName")}
        return None
