console.log('JavaScript is working!');

// Initialize the Leaflet map
const map = L.map('map').setView([51.505, -0.09], 13);

// Add a tile layer to the map
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

// Function to add an image marker
function addImageMarker(lat, lng, imageName) {
    // Use the Cloudflare Worker URL to access the image
    const icon = L.icon({
        iconUrl: `https://worker-cloudflare.renancatan4.workers.dev/${imageName}`, // Adjust path
        iconSize: [50, 50] // Customize the size as needed
    });

    // Add the marker to the map with the image icon
    const marker = L.marker([lat, lng], { icon }).addTo(map);

    // Optional: Bind a popup or additional actions
    marker.bindPopup(`<strong>${imageName}</strong>`);
}

// Example usage
addImageMarker(51.505, -0.09, 'renan-coffee.jpg'); // Adjust coordinates and image name
