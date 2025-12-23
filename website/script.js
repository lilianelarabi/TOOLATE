// ===============================
// Real-Time Dashboard Updater
// ===============================

const API_URL = "http://127.0.0.1:5000/data";

// Update current time
function updateClock() {
    const now = new Date();
    document.getElementById("current-time").textContent =
        now.toLocaleTimeString();
}

// Fetch data from Flask server
async function fetchTrafficData() {
    try {
        const response = await fetch(API_URL);
        const data = await response.json();

        // Top optimal lane
        document.getElementById("optimal-lane").textContent =
            `Lane ${data.optimal_lane}`;

        document.getElementById("recommended-lane-title").textContent =
            `Lane ${data.optimal_lane}`;

        document.getElementById("optimal-footer-text").textContent =
            data.optimization_note;

        // Vehicles
        document.getElementById("total-vehicles").textContent =
            data.total_vehicles;

        document.getElementById("footer-total-vehicles").textContent =
            data.total_vehicles;

        // Traffic status
        document.getElementById("traffic-status").textContent =
            data.traffic_status;

        // Active vehicles on optimal lane
        document.getElementById("active-vehicles").textContent =
            data.active_vehicles;

        // Lane capacity
        document.getElementById("lane-capacity-text").textContent =
            `${data.lane_capacity}%`;

        document.getElementById("lane-capacity-bar").style.width =
            `${data.lane_capacity}%`;

        // Emergency lane
        document.getElementById("emergency-lane").textContent =
            `Lane ${data.emergency_lane}`;

    } catch (error) {
        console.error("Server not reachable:", error);
    }
}

// Initial load
updateClock();
fetchTrafficData();

// Refresh every second
setInterval(updateClock, 1000);
setInterval(fetchTrafficData, 1000);
