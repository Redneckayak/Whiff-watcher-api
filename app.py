from flask import Flask, jsonify
from datetime import date
from mlb_api import MLBDataFetcher
from predictor import StrikeoutPredictor

app = Flask(__name__)

@app.route('/')
def index():
    return "Welcome to Whiff Watcher API!"

@app.route('/api/whiff-watch', methods=['GET'])
def generate_whiff_watch_data():
    fetcher = MLBDataFetcher()
    predictor = StrikeoutPredictor()

    today = date.today()
    games = fetcher.get_todays_games(today)

    matchups = []

    for game in games:
        for side in ['away', 'home']:
            pitcher_info = game.get(f'{side}_pitcher')
            if not pitcher_info:
                continue

            pitcher_stats = fetcher.get_pitcher_stats(pitcher_info['id'])
            if pitcher_stats['batters_faced'] < 50:
                continue  # Skip pitchers with low sample size

            team_name = game[f'{side}_team']
            team_id = fetcher.get_team_id_by_name(team_name)
            if not team_id:
                continue

            roster = fetcher.get_team_roster(team_id)
            for batter in roster:
                batter_stats = fetcher.get_batter_stats(batter['id'])
                if batter_stats['at_bats'] < 30:
                    continue  # Skip batters with low sample size

                matchup = {
                    'pitcher_name': pitcher_info['name'],
                    'pitcher_so_rate': pitcher_stats['so_rate'],
                    'pitcher_batters_faced': pitcher_stats['batters_faced'],
                    'batter_name': batter['name'],
                    'batter_so_rate': batter_stats['so_rate'],
                    'batter_at_bats': batter_stats['at_bats']
                }
                matchups.append(matchup)

    import pandas as pd
    matchups_df = pd.DataFrame(matchups)
    predictions_df = predictor.predict_strikeouts(matchups_df)

    if predictions_df.empty:
        return jsonify([])

    ranked_df = predictor.rank_predictions(predictions_df)
    output = ranked_df.head(10)[[
        'pitcher_name',
        'batter_name',
        'pitcher_so_rate',
        'batter_so_rate',
        'confidence_score',
        'strikeout_probability',
        'prediction_reason'
    ]].to_dict(orient='records')

    return jsonify(output)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
