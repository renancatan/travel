import { populateFilters, filterMarkers } from './filters/filters.js';

const map = L.map('map').setView([0, 0], 2);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
}).addTo(map);

const workerBaseURL = 'https://worker-cloudflare.renancatan4.workers.dev';
let allLocations = [];
let markers = [];

fetch('/metadata.json')
  .then(response => {
    if (!response.ok) {
      throw new Error('Network response was not ok ' + response.statusText);
    }
    return response.json();
  })
  .then(locations => {
    console.log('Locations data:', JSON.stringify(locations, null, 2));
    allLocations = locations;
    populateFilters(locations, 'regionFilter', 'categoryFilter');
    updateMarkers(locations);
  })
  .catch(error => {
    console.error('Failed to fetch metadata:', error);
  });

function removeMarkers() {
  markers.forEach(marker => {
    map.removeLayer(marker);
  });
  markers = [];
}

function processLocation(location, selectedRegion, selectedCategory) {
  console.log(`Processing location: ${location.city}, region: ${location.region}, categories: ${location.categories}`);
  console.log(`Selected region: ${selectedRegion}, selected category: ${selectedCategory}`);
  
  if (location.coordinates && location.coordinates.length === 2) {
    const regionMatches = selectedRegion === 'all' || location.region === selectedRegion;
    const categoryMatches = selectedCategory === 'all' || location.categories.includes(selectedCategory);

    if (regionMatches && categoryMatches) {
      console.log(`Adding marker for location: ${location.city}`);
      const marker = L.marker(location.coordinates).addTo(map);
      markers.push(marker);

      location.images.forEach((image, index) => {
        const category = getCategoryFromImageName(image, location.categories);
        let fullPath;

        if (location.region) {
          fullPath = `${workerBaseURL}/${location.country}/${location.region}/${location.province}/${location.city}/${category}/${image}`;
        } else {
          fullPath = `${workerBaseURL}/${location.country}/${location.province}/${location.city}/${category}/${image}`;
        }

        const icon = L.icon({
          iconUrl: fullPath,
          iconSize: [50, 50]
        });

        const imageMarker = L.marker(
          [location.coordinates[0] + index * 0.00025, location.coordinates[1] + index * 0.00025],
          { icon }
        ).addTo(map);
        imageMarker.bindPopup(`<strong>${fullPath}</strong>`);
        markers.push(imageMarker);
      });
    } else {
      console.log(`Skipping location: ${location.city}`);
    }
  } else {
    console.log(`Invalid coordinates for ${location.city}`);
  }
}

function getCategoryFromImageName(imageName, categories) {
  for (const category of categories) {
    if (imageName.includes(category)) {
      return category;
    }
  }
  return 'general';
}

function updateMarkers(locations) {
  console.log('Updating markers...');
  removeMarkers();
  const selectedRegion = document.getElementById('regionFilter').value;
  const selectedCategory = document.getElementById('categoryFilter').value;

  console.log(`Selected region: ${selectedRegion}, selected category: ${selectedCategory}`);
  
  locations.forEach(location => processLocation(location, selectedRegion, selectedCategory));
}

document.getElementById('regionFilter').addEventListener('change', () => {
  updateMarkers(allLocations);
});

document.getElementById('categoryFilter').addEventListener('change', () => {
  updateMarkers(allLocations);
});
