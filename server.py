from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Shared state (updated by realtime.py)
STATE = {
    "optimal_lane": 2,
    "optimization_note": "Waiting for data...",
    "total_vehicles": 0,
    "traffic_status": "Unknown",
    "active_vehicles": 0,
    "lane_capacity": 0,
    "emergency_lane": 3,
}

LANE_MAP = {"A": 4, "B": 2, "C": 1}  # map YOLO lanes → UI lanes
LANE_CAPACITY = 150


@app.route("/api/update", methods=["POST"])
def update_from_yolo():
    data = request.json

    lanes = data.get("lanes", {})
    emergency_lane = data.get("emergency_lane")

    # Determine optimal lane (least crowded, excluding emergency)
    sorted_lanes = sorted(
        lanes.items(),
        key=lambda x: x[1]
    )

    optimal_lane_letter, optimal_count = sorted_lanes[0]
    optimal_lane_ui = LANE_MAP.get(optimal_lane_letter, 2)

    total_vehicles = sum(lanes.values())
    capacity_percent = int((optimal_count / LANE_CAPACITY) * 100)

    traffic_status = (
        "Low Flow" if optimal_count < 30
        else "Moderate Flow" if optimal_count < 70
        else "Heavy Flow"
    )

    STATE.update({
        "optimal_lane": optimal_lane_ui,
        "optimization_note": "Least crowded route selected",
        "total_vehicles": total_vehicles,
        "traffic_status": traffic_status,
        "active_vehicles": optimal_count,
        "lane_capacity": capacity_percent,
        "emergency_lane": LANE_MAP.get(emergency_lane, 3),
    })

    return jsonify({"status": "ok"})


@app.route("/data")
def get_data():
    return jsonify(STATE)


if __name__ == "__main__":
    app.run(debug=True)
