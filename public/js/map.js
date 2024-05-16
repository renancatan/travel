import { locations } from './config.js';

console.log("Map script loaded!");  // Check if this message is logged

const map = L.map('map').setView([51.505, -0.09], 13);
console.log("Map initialized!");  // Check if this message is logged

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
}).addTo(map);
console.log("Tile layer added!");  // Check if this message is logged

Object.keys(locations).forEach(country => {
  console.log(`Country: ${country}`);  // Debugging
  Object.keys(locations[country]).forEach(region => {
    console.log(`Region: ${region}`);  // Debugging
    Object.keys(locations[country][region]).forEach(province => {
      console.log(`Province: ${province}`);  // Debugging
      Object.keys(locations[country][region][province]).forEach(city => {
        console.log(`City: ${city}`);  // Debugging
        const location = locations[country][region][province][city];
        const marker = L.marker(location.coordinates).addTo(map);
        console.log(`Marker added at: ${location.coordinates}`);  // Debugging

        marker.on('click', function() {
          const imageContainer = document.createElement('div');
          location.images.forEach(imageUrl => {
            const img = document.createElement('img');
            img.src = imageUrl;
            img.style.width = '100px';  // Adjust image size
            img.style.height = '100px'; // Adjust image size
            imageContainer.appendChild(img);
          });

          const popup = L.popup()
            .setLatLng(location.coordinates)
            .setContent(imageContainer)
            .openOn(map);

          console.log("Images added to pop-up!");  // Debugging
        });
      });
    });
  });
});
