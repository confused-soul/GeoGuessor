// Initialize the map
const map = L.map('map').setView([28.7041, 77.1025], 2);  // Default view (Delhi)

// Load and display a tile layer on the map with `noWrap: true`
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    noWrap: true  // Prevents the map from wrapping infinitely
}).addTo(map);

let marker;       // For user-selected marker
let correctMarker; // For the correct location marker
let isSubmitted = false; 

// Listen for clicks on the map to place a marker
map.on('click', function(e) {
    if (!isSubmitted) { // Only allow placing a marker if not submitted
        const lat = e.latlng.lat;
        const lon = e.latlng.lng;

        // If a marker exists, remove it
        if (marker) {
            map.removeLayer(marker);
        }

        // Place a new marker at the clicked location
        marker = L.marker([lat, lon]).addTo(map);
        marker.bindTooltip("Your Guess", {
            permanent: false,    // Tooltip will appear on hover only
            direction: "top",     // Position tooltip on top of the marker
            className: "custom-tooltip" 
        }).openTooltip();  
    }
});

// Send coordinates to the backend when "Submit" is clicked
document.getElementById('submitBtn').addEventListener('click', function() {
    if(!isSubmitted){
        if (marker) {
            const lat = marker.getLatLng().lat;
            const lon = marker.getLatLng().lng;

            fetch('/get_score', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ lat: lat, lon: lon })
            })
            .then(response => response.json())
            .then(data => {
                // Display the score and distance on the webpage
                document.getElementById('score').textContent = `Score: ${data.score}`;
                document.getElementById('distance').textContent = `Distance: ${data.distance} km`;
                document.getElementById('place-name').textContent = `Place: ${data.place_name}`;
                document.getElementById('place-location').textContent = `Location: ${data.place_location}`;

                // Update the average score and highscore displays
                if (data.average_score) {
                    document.getElementById('average_score-display').textContent = `Your Average Score: ${data.average_score}`;
                }
                if (data.highscore) {
                    document.getElementById('highscore-display').textContent = `Your Highest Score: ${data.highscore}`;
                }

                // Place a red marker at the correct location
                const correctLat = data.lat;
                const correctLon = data.lon;

                console.log('Correct Location:', correctLat, correctLon); // Debugging log

                // If a correct marker exists, remove it
                if (correctMarker) {
                    map.removeLayer(correctMarker);
                }

                // Add the correct location marker in red
                correctMarker = L.marker([correctLat, correctLon], {
                    icon: L.icon({
                        iconUrl: 'https://maps.google.com/mapfiles/ms/icons/red-dot.png',
                        iconSize: [32, 32], // Optional: adjust icon size
                        iconAnchor: [16, 32] // Optional: adjust icon anchor point
                    })
                }).addTo(map);

                correctMarker.bindTooltip("Correct Location", {
                    permanent: false,    // Tooltip will appear on hover only
                    direction: "top",     // Position tooltip on top of the marker
                    className: "custom-tooltip" 
                }).openTooltip();  
                
                isSubmitted = true;

                // Fit the map view to show both markers (if they exist)
                if (marker && correctMarker) {
                    const bounds = L.latLngBounds([marker.getLatLng(), [correctLat, correctLon]]);
                    map.fitBounds(bounds, { padding: [50, 50] });
                }
            })
            .catch(error => console.error('Error:', error));
        } else {
            alert('Please select a location on the map first.');
        }
    }
});

// Reload the page for a new place when "Next Place" button is clicked
document.getElementById('nextPlaceBtn').addEventListener('click', function() {
    location.reload();
});

function fetchNewPlace() {
    fetch('/get_place')
        .then(response => response.json())
        .then(data => {
            if (data.message) {
                alert(data.message);
            } else if (data.error) {
                alert('Error fetching place: ' + data.error);
            } else {
                // Assuming data contains the base64 image directly
                document.getElementById('image-area').innerHTML = `
                    <img src="data:image/jpeg;base64,${data.place}" alt="Place Image" style="max-width: 100%; height: auto;">
                `;
            }
        })
        .catch(error => console.error('Error fetching place:', error));
}

// Call fetchNewPlace when the game loads
window.onload = fetchNewPlace;