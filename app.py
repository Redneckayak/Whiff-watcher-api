from flask import Flask, jsonify
import pandas as pd
from predictor import StrikeoutPredictor
from mlb_api import fetch_today_matchups

app = Flask(__name__)

@app.route('/')
def home():
    return "Whiff Watcher API is running!"

@app.route('/api/whiff-watch')
def whiff_watch():
    try:
        # Load today’s pitcher/batter matchups from mlb_api
        matchups = fetch_today_matchups()

        # Create predictor and generate results
        predictor = StrikeoutPredictor()
        predictions = predictor.predict_strikeouts(matchups)

        # Rank and format predictions
        ranked = predictor.rank_predictions(predictions)
        result = ranked.to_dict(orient="records")

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
