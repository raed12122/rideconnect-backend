from flask import Flask, request, jsonify
from models import insert_ride_request, accept_ride_transaction

app = Flask(__name__)

# Home route
@app.route('/')
def home():
    return " RideConnect API is running!"

# Ride Request Endpoint
@app.route('/ride-request', methods=['POST'])
def request_ride():
    data = request.get_json()

    try:
        ride_id = insert_ride_request(data)
        return jsonify({
            "ride_id": ride_id,
            "status": "requested",
            "estimated_duration": data["estimated_duration"],
            "estimated_arrival_time": data["estimated_arrival_time"],
            "total_fare": data["total_fare"]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Ride Accept Endpoint
@app.route('/ride-accept', methods=['POST'])
def accept_ride():
    data = request.get_json()
    ride_id = data.get("ride_id")
    driver_id = data.get("driver_id")

    result = accept_ride_transaction(ride_id, driver_id)

    if result == "not_found":
        return jsonify({"error": "Ride not found"}), 404
    elif result == "unavailable":
        return jsonify({"error": "Ride already accepted or unavailable"}), 409

    return jsonify({
        "ride_id": ride_id,
        "driver_id": driver_id,
        "status": "accepted"
    })

# Run the app
if __name__ == '__main__':
    app.run(debug=True)