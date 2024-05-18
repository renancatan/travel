import { locations } from './config.js';

const map = L.map('map').setView([0, 0], 2);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
}).addTo(map);

const workerBaseURL = 'https://worker-cloudflare.renancatan4.workers.dev';

Object.keys(locations).forEach(country => {
  console.log(`Processing country: ${country}`);  
  Object.keys(locations[country]).forEach(region => {
    console.log(`Processing region: ${region}`);  
    Object.keys(locations[country][region]).forEach(province => {
      console.log(`Processing province: ${province}`);  
      Object.keys(locations[country][region][province]).forEach(city => {
        console.log(`Processing city: ${city}`);  
        const location = locations[country][region][province][city];
        console.log(`Location details: ${JSON.stringify(location)}`);  

        // Verify if location coordinates are valid
        if (location.coordinates && location.coordinates.length === 2) {
          const marker = L.marker(location.coordinates).addTo(map);
          console.log(`Marker added at: ${location.coordinates}`);  

          location.images.forEach((image, index) => {
            const fullPath = `${workerBaseURL}/${country}/${region}/${province}/${city}/${image}`;
            console.log(`Full Path: ${fullPath}`);  

            const icon = L.icon({
              iconUrl: fullPath,
              iconSize: [50, 50]
            });

            const imageMarker = L.marker([location.coordinates[0] + index * 0.00025, location.coordinates[1] + index * 0.00025], { icon }).addTo(map);
            imageMarker.bindPopup(`<strong>${fullPath}</strong>`);
          });
        } else {
          console.log(`Invalid coordinates for ${city}`);  
        }
      });
    });
  });
});
