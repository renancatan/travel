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
  .then(primaryData => {
    console.log('Primary data:', JSON.stringify(primaryData, null, 2));

    fetch('/data')
      .then(response => {
        if (!response.ok) {
          throw new Error('Network response was not ok ' + response.statusText);
        }
        return response.json();
      })
      .then(secondaryData => {
        console.log('Google Sheets data:', JSON.stringify(secondaryData, null, 2));
        const mergedData = mergeData(primaryData, secondaryData);
        allLocations = mergedData;
        populateFilters(mergedData, 'regionFilter', 'categoryFilter');
        updateMarkers(mergedData);
      })
      .catch(error => {
        console.error('Failed to fetch data:', error);
        allLocations = primaryData;
        populateFilters(primaryData, 'regionFilter', 'categoryFilter');
        updateMarkers(primaryData);
      });
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

      const tooltip = L.tooltip({
        permanent: true,
        direction: 'top'
      }).setContent(location.city);
      marker.bindTooltip(tooltip);

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

function mergeData(primaryData, secondaryData) {
  const primaryMap = new Map();
  primaryData.forEach(item => primaryMap.set(item.city, item));

  secondaryData.forEach(item => {
    if (primaryMap.has(item.city)) {
      const primaryItem = primaryMap.get(item.city);
      primaryItem.categories = [...new Set([...primaryItem.categories, ...item.categories])];
      primaryItem.images = [...new Set([...primaryItem.images, ...item.images])];
      primaryItem.region = primaryItem.region || item.region;
      primaryItem.country = primaryItem.country || item.country;
      primaryItem.province = primaryItem.province || item.province;
      primaryItem.coordinates = primaryItem.coordinates.length ? primaryItem.coordinates : item.coordinates;
    } else {
      primaryMap.set(item.city, item);
    }
  });

  return Array.from(primaryMap.values());
}
