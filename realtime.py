import cv2
import numpy as np
from ultralytics import YOLO
import time
import requests

FLASK_URL = "http://127.0.0.1:5000/api/update"

# ------------------ USER TUNABLE PARAMETERS ------------------
MODEL_PATH = "best.pt"            # place best.pt in same folder
CAM_INDEX = 0                     # change if another webcam
CONGESTION_THRESHOLD = 5          # >5 => CONGESTED

# Lane fractions (top to bottom)
LANE_Y_FRACS = (0.00, 0.26, 0.62)

DEST_X_FRAC = 0.18  # leftmost 18% width considered destination
# ------------------------------------------------------------

# Validate lane fractions
if not (0 <= LANE_Y_FRACS[0] < LANE_Y_FRACS[1] < LANE_Y_FRACS[2] <= 1.0):
    raise ValueError("LANE_Y_FRACS must be increasing fractions within [0,1].")

print("Loading model...")
model = YOLO(MODEL_PATH)
print("Model loaded.")

# Class map (adjust if your dataset differs)
CLASS_MAP = {
    0: "driver",
    1: "emergency",
    2: "small"
}

def get_lane_from_y(y, h):
    f1 = int(LANE_Y_FRACS[1] * h)
    f2 = int(LANE_Y_FRACS[2] * h)
    if y < f1:
        return "C"
    elif y < f2:
        return "B"
    else:
        return "A"

def lane_state_str(count):
    if count > CONGESTION_THRESHOLD:
        return "CONGESTED"
    elif count > 0:
        return "NORMAL"
    else:
        return "EMPTY"

def is_in_destination(cx, w):
    return cx <= int(DEST_X_FRAC * w)

# Open webcam
cap = cv2.VideoCapture(CAM_INDEX)
if not cap.isOpened():
    raise RuntimeError("Could not open webcam. Change CAM_INDEX if needed.")

print("Starting real-time detection. Press 'q' to quit.")
fps_time = time.time()

while True:
    ret, frame = cap.read()
    if not ret:
        print("Frame not received. Exiting.")
        break

    h, w, _ = frame.shape

    lane_counts = {"A": 0, "B": 0, "C": 0}
    driver_lane = None
    emergency_lane = None
    driver_in_destination = False

    # YOLO inference
    t0 = time.time()
    results = model(frame, verbose=False)[0]
    inference_time_ms = (time.time() - t0) * 1000

    for box in results.boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        label = CLASS_MAP.get(cls_id, f"id{cls_id}")

        cx = int((x1 + x2) / 2)
        cy = int((y1 + y2) / 2)

        lane = get_lane_from_y(cy, h)

        if label == "small":
            lane_counts[lane] += 1

        if label == "driver":
            driver_lane = lane
            if is_in_destination(cx, w):
                driver_in_destination = True

        if label == "emergency":
            emergency_lane = lane

        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(
            frame,
            f"{label} {conf:.2f} | {lane}",
            (x1, y1 - 8),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            2,
        )
        cv2.circle(frame, (cx, cy), 3, (0, 255, 255), -1)

    # Emergency logic
    alert_text = ""
    if emergency_lane == "C":
        alert_text = "EMERGENCY IN LANE C!"
        if driver_lane == "C":
            alert_text = "!!! DRIVER: MOVE OUT OF LANE C !!!"

    # Overlay info
    cv2.putText(frame, f"Lane A Count: {lane_counts['A']}", (10, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 200), 2)
    cv2.putText(frame, f"Lane B Count: {lane_counts['B']}", (10, 45),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 0), 2)
    cv2.putText(frame, f"Lane C Count: {lane_counts['C']}", (10, 70),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 0), 2)

    if alert_text:
        cv2.putText(frame, alert_text, (10, 110),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 3)

    if driver_in_destination:
        cv2.putText(frame, "Driver reached DESTINATION Y", (10, 150),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 128, 255), 2)

    # Lane lines
    f1 = int(LANE_Y_FRACS[1] * h)
    f2 = int(LANE_Y_FRACS[2] * h)
    cv2.line(frame, (0, f1), (w, f1), (255, 255, 255), 1)
    cv2.line(frame, (0, f2), (w, f2), (255, 255, 255), 1)

    dest_x = int(DEST_X_FRAC * w)
    cv2.rectangle(frame, (0, 0), (dest_x, h), (255, 255, 255), 2)

    # FPS
    now = time.time()
    fps = 1.0 / (now - fps_time) if now > fps_time else 0.0
    fps_time = now
    cv2.putText(frame, f"FPS: {fps:.1f}", (w - 120, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    # Send to Flask
    payload = {
        "lanes": lane_counts,
        "confidence": round(
            float(np.mean(results.boxes.conf.cpu().numpy())) * 100
            if len(results.boxes) else 0,
            2,
        ),
        "inference_time": round(inference_time_ms, 2),
        "driver_lane": driver_lane,
        "emergency_lane": emergency_lane,
        "driver_in_destination": driver_in_destination,
    }

    try:
        requests.post(FLASK_URL, json=payload, timeout=0.1)
    except requests.exceptions.RequestException:
        pass

    cv2.imshow("Intelligent Road Prototype", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
