import { populateFilters, filterMarkers } from './filters/filters.js';

const map = L.map('map').setView([0, 0], 2);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
}).addTo(map);

const workerBaseURL = 'https://worker-cloudflare.renancatan4.workers.dev';
let allLocations = [];
let markers = [];

const categoryIcons = {
  bars: L.icon({ iconUrl: `${workerBaseURL}/utils/icons/bar.png`, iconSize: [40, 40] }),
  beaches: L.icon({ iconUrl: `${workerBaseURL}/utils/icons/beach.png`, iconSize: [50, 50] }),
  caves: L.icon({ iconUrl: `${workerBaseURL}/utils/icons/cave.png`, iconSize: [50, 50] }),
  general: L.icon({ iconUrl: `${workerBaseURL}/utils/icons/default.png`, iconSize: [40, 40] }),
  default: L.icon({ iconUrl: `${workerBaseURL}/utils/icons/default.png`, iconSize: [40, 40] })
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
      
      const category = location.categories.length > 0 ? location.categories[0] : 'general';
      const icon = categoryIcons[category] || categoryIcons.default;

      const marker = L.marker(location.coordinates, { icon }).addTo(map);
      markers.push(marker);

      const tooltip = L.tooltip({
        permanent: true,
        direction: 'top'
      }).setContent(location.city);
      marker.bindTooltip(tooltip);

      marker.on('click', () => openModal(location));

      if (location.subLocations) {
        location.subLocations.forEach(subLoc => {
          const subCategory = subLoc.category || 'general';
          const subIcon = categoryIcons[subCategory] || categoryIcons.default;
          const subMarker = L.marker(subLoc.coordinates, { icon: subIcon }).addTo(map);
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
  const modalTitle = document.getElementById('modal-title');
  const modalBody = document.getElementById('modal-body');
  const modalImages = document.getElementById('modal-images');

  if (!modal || !modalTitle || !modalBody || !modalImages) {
      console.error('One or more modal elements are missing.');
      return;
  }

  const title = parentLocation ? `${parentLocation.city} - ${location.name}` : location.city;
  const bodyText = `
      <table>
          <tr>
              <td><strong>Name:</strong></td>
              <td>${location.name}</td>
          </tr>
          <tr>
              <td><strong>Score:</strong></td>
              <td>${location.score || parentLocation?.score || 'N/A'}</td>
          </tr>
      </table>
      Price: ${location.prices || parentLocation?.prices || 'N/A'} ${location.additionalInfo || parentLocation?.additionalInfo || 'N/A'}
  `;
  const images = location.images.length > 0 ? location.images : parentLocation ? parentLocation.images : [];

  modalTitle.textContent = title;
  modalBody.innerHTML = bodyText;
  modalImages.innerHTML = '';

  images.forEach((image, index) => {
      if (!/^(jpg|jpeg|png|gif)$/.test(image.split('.').pop())) return;

      let fullPath;
      const category = location.categories.length > 0 ? location.categories[0] : (parentLocation ? parentLocation.categories[0] : 'general');

      const country = location.country || parentLocation?.country || 'unknown';
      const region = location.region || parentLocation?.region || '';
      const province = location.province || parentLocation?.province || 'unknown';
      const city = location.city || parentLocation?.city || 'unknown';
      const subLocationName = location.isSublocation ? location.name.toLowerCase().replace(/ /g, '_') : '';

      if (location.isSublocation) {
          fullPath = `${workerBaseURL}/${country}/${region}/${province}/${city}/${category}/${subLocationName}/${image}`;
      } else {
          fullPath = `${workerBaseURL}/${country}/${region}/${province}/${city}/${category}/${image}`;
      }

      const imgElement = document.createElement('img');
      imgElement.src = fullPath;
      imgElement.alt = `Image ${index + 1}`;
      modalImages.appendChild(imgElement);
  });

  const videos = location.videos.length > 0 ? location.videos : parentLocation ? parentLocation.videos : [];
  videos.forEach((video, index) => {
      if (video.includes("youtube.com/embed/")) {
          const iframeElement = document.createElement('iframe');
          iframeElement.src = video;
          iframeElement.width = "560";
          iframeElement.height = "315";
          iframeElement.frameBorder = "0";
          iframeElement.allow = "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture";
          iframeElement.allowFullscreen = true;
          modalImages.appendChild(iframeElement);
      } else {
          const errorText = document.createElement('p');
          errorText.textContent = `Video URL is not embeddable: ${video}`;
          modalImages.appendChild(errorText);
      }
  });

  modal.style.display = 'block';
}

document.getElementById('modal-close').addEventListener('click', () => {
  const modal = document.getElementById('locationModal');
  if (modal) {
    modal.style.display = 'none';
  }
});

document.addEventListener('click', event => {
  const modal = document.getElementById('locationModal');
  if (event.target === modal) {
    modal.style.display = 'none';
  }
});
