from flask import Flask, jsonify, Response
import json
from datetime import date
from predictor import StrikeoutPredictor
from mlb_api import MLBDataFetcher

app = Flask(__name__)

@app.route('/')
def home():
    return 'Whiff Watcher API is running!'

@app.route('/api/whiff-watch', methods=['GET'])
def generate_whiff_watch_data():
    try:
        # Initialize helpers
        fetcher = MLBDataFetcher()
        predictor = StrikeoutPredictor()

        # Get today’s matchups
        matchups = fetcher.get_todays_games(date.today())
        all_data = []

        for game in matchups:
            for side in ['home', 'away']:
                pitcher = game.get(f'{side}_pitcher')
                team_name = game.get(f'{side}_team')
                
                if not pitcher or not team_name:
                    continue
                
                team_id = fetcher.get_team_id_by_name(team_name)
                if not team_id:
                    continue

                batters = fetcher.get_team_roster(team_id)
                pitcher_stats = fetcher.get_pitcher_stats(pitcher['id'])

                for batter in batters:
                    batter_stats = fetcher.get_batter_stats(batter['id'])
                    if batter_stats['at_bats'] < 10:
                        continue  # skip players with small sample sizes

                    row = {
                        'batter_name': batter['name'],
                        'pitcher_name': pitcher['name'],
                        'batter_so_rate': batter_stats['so_rate'],
                        'pitcher_so_rate': pitcher_stats['so_rate'],
                        'batter_at_bats': batter_stats['at_bats'],
                        'pitcher_batters_faced': pitcher_stats['batters_faced']
                    }

                    all_data.append(row)

        import pandas as pd
        df = pd.DataFrame(all_data)
        predictions = predictor.predict_strikeouts(df)

        if predictions.empty:
            return jsonify([])

        # Format response
        json_data = predictions[[
            'batter_name',
            'batter_so_rate',
            'confidence_score',
            'pitcher_name',
            'pitcher_so_rate',
            'prediction_reason',
            'strikeout_probability'
        ]].to_dict(orient='records')

        return Response(json.dumps(json_data, indent=2), mimetype='application/json')

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=10000)
