from flask import Flask, jsonify
from datetime import datetime
import pandas as pd
from mlb_api import MLBDataFetcher
from predictor import StrikeoutPredictor

app = Flask(__name__)

@app.route('/api/whiff-watch')
def whiff_watch():
    try:
        fetcher = MLBDataFetcher()
        predictor = StrikeoutPredictor()

        today = datetime.now().date()
        games = fetcher.get_todays_games(today)

        matchups = []

        for game in games:
            for team_type in ['home', 'away']:
                pitcher_info = game[f'{team_type}_pitcher']
                team_name = game[f'{team_type}_team']

                if not pitcher_info:
                    continue

                pitcher_stats = fetcher.get_pitcher_stats(pitcher_info['id'])
                if not pitcher_stats or pitcher_stats['batters_faced'] == 0:
                    continue

                team_id = fetcher.get_team_id_by_name(team_name)
                if not team_id:
                    continue

                batters = fetcher.get_team_roster(team_id)

                for batter in batters:
                    batter_stats = fetcher.get_batter_stats(batter['id'])
                    if not batter_stats or batter_stats['at_bats'] == 0:
                        continue

                    matchup = {
                        'batter_name': batter['name'],
                        'batter_so_rate': batter_stats['so_rate'],
                        'batter_at_bats': batter_stats['at_bats'],
                        'pitcher_name': pitcher_info['name'],
                        'pitcher_so_rate': pitcher_stats['so_rate'],
                        'pitcher_batters_faced': pitcher_stats['batters_faced']
                    }
                    matchups.append(matchup)

        df = pd.DataFrame(matchups)
        top_predictions = predictor.predict_strikeouts(df)

        result = top_predictions.to_dict(orient='records')
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
