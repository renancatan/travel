import { populateFilters, filterMarkers } from './filters/filters.js';

const map = L.map('map').setView([0, 0], 2);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
}).addTo(map);

const workerBaseURL = 'https://worker-cloudflare.renancatan4.workers.dev';
let allLocations = [];
let markers = [];

const categoryIcons = {
  bar: L.icon({ iconUrl: `${workerBaseURL}/path/to/bar-icon.png`, iconSize: [30, 30] }),
  beach: L.icon({ iconUrl: `${workerBaseURL}/path/to/beach-icon.png`, iconSize: [30, 30] }),
  cave: L.icon({ iconUrl: `${workerBaseURL}/path/to/cave-icon.png`, iconSize: [30, 30] }),
  default: L.icon({ iconUrl: `${workerBaseURL}/path/to/default-icon.png`, iconSize: [40, 40] })
};

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
        const mergedData = primaryData.concat(secondaryData);
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
      
      // Choose icon based on category
      const category = location.categories.length > 0 ? location.categories[0] : 'default';
      const icon = categoryIcons[category] || categoryIcons.default;

      const marker = L.marker(location.coordinates, { icon }).addTo(map);
      markers.push(marker);

      const tooltip = L.tooltip({
        permanent: true,
        direction: 'top'
      }).setContent(location.city);
      marker.bindTooltip(tooltip);

      marker.on('click', () => openModal(location));
      
      // Add markers for sub-locations
      if (location.subLocations) {
        location.subLocations.forEach(subLoc => {
          const subMarker = L.marker(subLoc.coordinates, { icon }).addTo(map);
          markers.push(subMarker);

          const subTooltip = L.tooltip({
            permanent: true,
            direction: 'top'
          }).setContent(`${location.city} - ${subLoc.name}`);
          subMarker.bindTooltip(subTooltip);

          subMarker.on('click', () => openModal(subLoc, location));
        });
      }

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

function openModal(location, parentLocation = null) {
  const modal = document.getElementById('locationModal');
  const modalContent = document.getElementById('modal-content');
  const modalTitle = document.getElementById('modal-title');
  const modalBody = document.getElementById('modal-body');
  const modalImages = document.getElementById('modal-images');
  const modalInfo = document.getElementById('modal-info');

  modalTitle.textContent = parentLocation ? `${parentLocation.city} - ${location.name}` : location.city;
  modalBody.textContent = `Price: ${location.prices || 'N/A'}\n${location.additionalInfo || 'No additional info'}`;
  modalImages.innerHTML = '';

  location.images.forEach((image, index) => {
    const category = getCategoryFromImageName(image, location.categories);
    let fullPath;
    if (parentLocation && parentLocation.region) {
      fullPath = `${workerBaseURL}/${parentLocation.country}/${parentLocation.region}/${parentLocation.province}/${parentLocation.city}/${category}/${location.name}/${image}`;
    } else if (parentLocation) {
      fullPath = `${workerBaseURL}/${parentLocation.country}/${parentLocation.province}/${parentLocation.city}/${category}/${location.name}/${image}`;
    } else if (location.region) {
      fullPath = `${workerBaseURL}/${location.country}/${location.region}/${location.province}/${location.city}/${category}/${image}`;
    } else {
      fullPath = `${workerBaseURL}/${location.country}/${location.province}/${location.city}/${category}/${image}`;
    }

    const imgElement = document.createElement('img');
    imgElement.src = fullPath;
    imgElement.alt = `Image ${index + 1}`;
    modalImages.appendChild(imgElement);
  });

  modal.style.display = 'block';
}

document.getElementById('modal-close').addEventListener('click', () => {
  document.getElementById('locationModal').style.display = 'none';
});

document.addEventListener('click', event => {
  if (event.target == document.getElementById('locationModal')) {
    document.getElementById('locationModal').style.display = 'none';
  }
});
