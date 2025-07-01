from flask import Flask, jsonify, send_from_directory
from predictor import generate_whiff_watch_data
import os
import json

app = Flask(__name__)

@app.route("/")
def root():
    return jsonify({"message": "Whiff Watcher API is live"})

@app.route("/api/whiff-watch")
def whiff_watch_api():
    try:
        data = generate_whiff_watch_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/generate-json")
def generate_json():
    try:
        data = generate_whiff_watch_data()
        os.makedirs("static", exist_ok=True)
        with open("static/whiff_watch_data.json", "w") as f:
            json.dump(data, f, indent=2)
        return jsonify({"message": "JSON generated", "path": "/static/whiff_watch_data.json"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/static/<path:filename>")
def static_file(filename):
    return send_from_directory("static", filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
