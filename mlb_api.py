import requests
import json
from datetime import datetime, date
from typing import List, Dict, Optional
import streamlit as st

class MLBDataFetcher:
    """Handles all MLB API data fetching operations"""
    
    def __init__(self):
        self.base_url = "https://statsapi.mlb.com/api/v1"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'WhiffWatcher/1.0'
        })
    
    @st.cache_data(ttl=300)
    def get_todays_games(_self, target_date: date) -> List[Dict]:
        """Fetch today's MLB games with starting lineups"""
        
        date_str = target_date.strftime('%Y-%m-%d')
        
        try:
            # Get schedule for the date with lineup data
            schedule_url = f"{_self.base_url}/schedule"
            params = {
                'sportId': 1,  # MLB
                'date': date_str,
                'hydrate': 'team,linescore,probablePitcher,lineups'
            }
            
            response = _self.session.get(schedule_url, params=params, timeout=10)
            response.raise_for_status()
            
            schedule_data = response.json()
            
            if not schedule_data.get('dates'):
                return []
            
            games = []
            for date_info in schedule_data['dates']:
                for game in date_info.get('games', []):
                    # Include all games (Preview, Live, Final) to get matchup data
                    game_info = _self._extract_game_info(game)
                    if game_info:
                        games.append(game_info)
            
            return games
            
        except requests.RequestException as e:
            raise Exception(f"Failed to fetch MLB schedule: {str(e)}")
        except Exception as e:
            raise Exception(f"Error processing MLB data: {str(e)}")
    
    def _extract_game_info(self, game: Dict) -> Optional[Dict]:
        """Extract relevant game information"""
        
        try:
            game_id = game['gamePk']
            
            # Extract team information
            away_team = game['teams']['away']['team']['name']
            home_team = game['teams']['home']['team']['name']
            
            # Extract probable pitchers
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
            
            # Game time
            game_time = game.get('gameDate')
            
            return {
                'game_id': game_id,
                'away_team': away_team,
                'home_team': home_team,
                'away_pitcher': away_pitcher,
                'home_pitcher': home_pitcher,
                'game_time': game_time,
                'status': game.get('status', {}).get('detailedState', 'Unknown')
            }
            
        except KeyError as e:
            st.warning(f"Missing game data field: {str(e)}")
            return None
    
    @st.cache_data(ttl=3600)
    def get_pitcher_stats(_self, pitcher_id: int, season: int = None) -> Dict:
        """Get pitcher statistics for strikeout rate calculation"""
        
        if season is None:
            season = datetime.now().year
            
        # Try current season first, then fallback to previous season
        seasons_to_try = [season, season - 1]
        
        for try_season in seasons_to_try:
            try:
                stats_url = f"{_self.base_url}/people/{pitcher_id}/stats"
                params = {
                    'stats': 'season',
                    'group': 'pitching',
                    'season': try_season
                }
                
                response = _self.session.get(stats_url, params=params, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                
                # Extract pitching stats
                if data.get('stats') and len(data['stats']) > 0:
                    if data['stats'][0].get('splits') and len(data['stats'][0]['splits']) > 0:
                        stats = data['stats'][0]['splits'][0]['stat']
                        
                        strikeouts = float(stats.get('strikeOuts', 0))
                        batters_faced = float(stats.get('battersFaced', 0))
                        
                        if batters_faced > 0:
                            so_rate = (strikeouts / batters_faced) * 100
                            return {
                                'strikeouts': strikeouts,
                                'batters_faced': batters_faced,
                                'so_rate': so_rate,
                                'innings_pitched': float(stats.get('inningsPitched', 0)),
                                'era': float(stats.get('era', 0.0))
                            }
            except:
                continue
        
        return {'so_rate': 0.0, 'strikeouts': 0, 'batters_faced': 0}
    
    @st.cache_data(ttl=3600)
    def get_team_roster(_self, team_id: int) -> List[Dict]:
        """Get complete team roster including all batters"""
        
        try:
            # Try multiple roster types to get comprehensive data
            roster_types = ['active', 'fullSeason', '40Man']
            all_batters = {}  # Use dict to avoid duplicates
            
            for roster_type in roster_types:
                try:
                    roster_url = f"{_self.base_url}/teams/{team_id}/roster"
                    params = {'rosterType': roster_type}
                    
                    response = _self.session.get(roster_url, params=params, timeout=10)
                    response.raise_for_status()
                    
                    data = response.json()
                    
                    for player in data.get('roster', []):
                        # Include all non-pitcher positions (Infielder, Outfielder, Catcher)
                        if player['position']['type'] != 'Pitcher':
                            player_id = player['person']['id']
                            if player_id not in all_batters:
                                all_batters[player_id] = {
                                    'id': player_id,
                                    'name': player['person']['fullName'],
                                    'position': player['position']['name']
                                }
                except Exception as e:
                    print(f"DEBUG: Failed to get {roster_type} roster for team {team_id}: {e}")
                    continue  # Try next roster type if this one fails
            
            roster = list(all_batters.values())

            

            
            return roster
            
        except requests.RequestException as e:
            st.warning(f"Failed to fetch team roster: {str(e)}")
            return []
        except Exception as e:
            st.warning(f"Error processing roster data: {str(e)}")
            return []
    
    @st.cache_data(ttl=3600)
    def get_batter_stats(_self, batter_id: int, season: int = None) -> Dict:
        """Get batter statistics for strikeout rate calculation"""
        
        if season is None:
            season = datetime.now().year
        
        # Try current season first, then fallback to previous season
        seasons_to_try = [season, season - 1]
        
        for try_season in seasons_to_try:
            try:
                stats_url = f"{_self.base_url}/people/{batter_id}/stats"
                params = {
                    'stats': 'season',
                    'group': 'hitting',
                    'season': try_season
                }
                
                response = _self.session.get(stats_url, params=params, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                
                # Extract hitting stats
                if data.get('stats') and len(data['stats']) > 0:
                    if data['stats'][0].get('splits') and len(data['stats'][0]['splits']) > 0:
                        stats = data['stats'][0]['splits'][0]['stat']
                        
                        strikeouts = float(stats.get('strikeOuts', 0))
                        at_bats = float(stats.get('atBats', 0))
                        
                        if at_bats > 0:
                            so_rate = (strikeouts / at_bats) * 100
                            return {
                                'strikeouts': strikeouts,
                                'at_bats': at_bats,
                                'so_rate': so_rate,
                                'avg': float(stats.get('avg', 0.0)),
                                'ops': float(stats.get('ops', 0.0))
                            }
            except:
                continue
        
        return {'so_rate': 0.0, 'strikeouts': 0, 'at_bats': 0}
    
    @st.cache_data(ttl=3600)
    def get_team_id_by_name(_self, team_name: str) -> Optional[int]:
        """Get team ID by team name"""
        
        try:
            teams_url = f"{_self.base_url}/teams"
            params = {'sportId': 1}
            
            response = _self.session.get(teams_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            for team in data.get('teams', []):
                if team['name'] == team_name:
                    return team['id']
            
            return None
            
        except Exception as e:
            st.warning(f"Failed to get team ID for {team_name}: {str(e)}")
            return None
