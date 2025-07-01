from flask import Flask, jsonify
from predictor import generate_whiff_watch_data
import os

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"message": "Welcome to the Whiff Watcher API!"})

@app.route('/api/whiff-watch', methods=['GET'])
def whiff_watch():
    try:
        data = generate_whiff_watch_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))  # Default to 10000 if PORT not set
    app.run(debug=False, host='0.0.0.0', port=port)
