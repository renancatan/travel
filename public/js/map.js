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
      .then(mergedData => {
        console.log('Merged data:', JSON.stringify(mergedData, null, 2));
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

      marker.on('click', () => {
        showImageModal(location);
      });

      const tooltip = L.tooltip({
        permanent: true,
        direction: 'top'
      }).setContent(`${location.city} - Price: ${location.prices}`);
      marker.bindTooltip(tooltip);
    } else {
      console.log(`Skipping location: ${location.city}`);
    }
  } else {
    console.log(`Invalid coordinates for ${location.city}`);
  }
}

function showImageModal(location) {
  const modal = document.getElementById('imageModal');
  const modalTitle = document.getElementById('modalTitle');
  const modalBody = document.getElementById('modalBody');
  const modalInfo = document.getElementById('modalInfo');

  modalTitle.innerText = location.city;
  modalInfo.innerHTML = `Price: ${location.prices}<br>${location.additionalInfo}`;
  modalBody.innerHTML = '';

  location.images.forEach(image => {
    const imgElement = document.createElement('img');
    const category = getCategoryFromImageName(image, location.categories);
    let fullPath;

    if (location.region) {
      fullPath = `${workerBaseURL}/${location.country}/${location.region}/${location.province}/${location.city}/${category}/${image}`;
    } else {
      fullPath = `${workerBaseURL}/${location.country}/${location.province}/${location.city}/${category}/${image}`;
    }

    imgElement.src = fullPath;
    modalBody.appendChild(imgElement);
  });

  modal.style.display = 'block';

  // Close the modal
  const closeBtn = document.getElementsByClassName('close')[0];
  closeBtn.onclick = function() {
    modal.style.display = 'none';
  };

  window.onclick = function(event) {
    if (event.target == modal) {
      modal.style.display = 'none';
    }
  };
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
