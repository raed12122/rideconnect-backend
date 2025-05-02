from flask import Flask, request, jsonify
from models import insert_ride, accept_ride

app = Flask(__name__)

@app.route('/')
def home():
    return "RideConnect API is running!"

@app.route('/ride-request', methods=['POST'])
def ride_request():
    data = request.get_json()
    try:
        result = insert_ride(data)
        return jsonify({
            "ride_id": result["ride_id"],
            "status": "requested",
            "estimated_duration": result["estimated_duration"],
            "estimated_fare": result["estimated_fare"],
            "estimated_arrival": result["estimated_arrival"]
        })
    except Exception as e:
        
        return jsonify({"error": str(e)}), 500

@app.route('/ride-accept', methods=['POST'])
def ride_accept():
    data = request.get_json()
    try:
        result = accept_ride(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
if __name__ == '__main__':
    app.run(debug=True)