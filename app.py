from flask import Flask, jsonify
from datetime import date
from mlb_api import MLBDataFetcher
from predictor import StrikeoutPredictor

app = Flask(__name__)

@app.route('/')
def index():
    return 'Welcome to Whiff Watcher API!'

@app.route('/api/whiff-watch', methods=['GET'])
def whiff_watch():
    try:
        fetcher = MLBDataFetcher()
        predictor = StrikeoutPredictor()

        # Get today’s matchups
        games = fetcher.get_todays_games(date.today())
        if not games:
            return jsonify({'error': 'No games found'}), 404

        # Prepare matchups for prediction
        matchups = []
        for game in games:
            for team_side in ['away_pitcher', 'home_pitcher']:
                pitcher = game.get(team_side)
                if pitcher:
                    team_name = game['away_team'] if team_side == 'away_pitcher' else game['home_team']
                    team_id = fetcher.get_team_id_by_name(team_name)
                    if team_id is None:
                        continue

                    roster = fetcher.get_team_roster(team_id)
                    pitcher_stats = fetcher.get_pitcher_stats(pitcher['id'])
                    if pitcher_stats['so_rate'] == 0:
                        continue

                    for batter in roster:
                        batter_stats = fetcher.get_batter_stats(batter['id'])
                        if batter_stats['so_rate'] == 0:
                            continue

                        matchups.append({
                            'game_id': game['game_id'],
                            'pitcher_name': pitcher['name'],
                            'batter_name': batter['name'],
                            'pitcher_so_rate': pitcher_stats['so_rate'],
                            'pitcher_batters_faced': pitcher_stats['batters_faced'],
                            'batter_so_rate': batter_stats['so_rate'],
                            'batter_at_bats': batter_stats['at_bats'],
                        })

        import pandas as pd
        matchups_df = pd.DataFrame(matchups)

        ranked_predictions = predictor.rank_predictions(
            predictor.predict_strikeouts(matchups_df)
        )

        top_predictions = ranked_predictions.head(10).to_dict(orient='records')
        return jsonify(top_predictions)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
