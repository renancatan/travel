import { locations } from './config.js';

const map = L.map('map').setView([0, 0], 2);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
}).addTo(map);

const workerBaseURL = 'https://worker-cloudflare.renancatan4.workers.dev';

console.log('Locations data:', JSON.stringify(locations, null, 2));

Object.keys(locations).forEach(country => {
  console.log(`Processing country: ${country}`);
  const countryData = locations[country];
  console.log('Country data:', countryData);

  if (countryData.regions && Object.keys(countryData.regions).length > 0) {
    Object.keys(countryData.regions).forEach(region => {
      const regionData = countryData.regions[region];
      console.log(`Processing region: ${region}`);
      console.log('Region data:', regionData);

      Object.keys(regionData.provinces).forEach(province => {
        const provinceData = regionData.provinces[province];
        console.log(`Processing province: ${province}`);
        console.log('Province data:', provinceData);

        Object.keys(provinceData.cities).forEach(city => {
          const cityData = provinceData.cities[city];
          console.log(`Processing city: ${city}`);
          processLocation(country, region, province, city, cityData);
        });
      });
    });
  } else if (countryData.provinces && Object.keys(countryData.provinces).length > 0) {
    Object.keys(countryData.provinces).forEach(province => {
      const provinceData = countryData.provinces[province];
      console.log(`Processing province: ${province}`);
      console.log('Province data:', provinceData);

      Object.keys(provinceData.cities).forEach(city => {
        const cityData = provinceData.cities[city];
        console.log(`Processing city: ${city}`);
        processLocation(country, null, province, city, cityData);
      });
    });
  }
});

function processLocation(country, region, province, locationName, locationData) {
  console.log(`Location details: ${JSON.stringify(locationData)}`);

  if (locationData.coordinates && locationData.coordinates.length === 2) {
    const marker = L.marker(locationData.coordinates).addTo(map);
    console.log(`Marker added at: ${locationData.coordinates}`);

    locationData.images.forEach((image, index) => {
      const category = getCategoryFromImageName(image, locationData.categories);
      let fullPath;

      if (region && province) {
        fullPath = `${workerBaseURL}/${country}/${region}/${province}/${locationName}/${category}/${image}`;
      } else if (region) {
        fullPath = `${workerBaseURL}/${country}/${region}/${locationName}/${category}/${image}`;
      } else {
        fullPath = `${workerBaseURL}/${country}/${province}/${locationName}/${category}/${image}`;
      }

      console.log(`Full Path: ${fullPath}`);

      const icon = L.icon({
        iconUrl: fullPath,
        iconSize: [50, 50]
      });

      const imageMarker = L.marker(
        [locationData.coordinates[0] + index * 0.00025, locationData.coordinates[1] + index * 0.00025],
        { icon }
      ).addTo(map);
      imageMarker.bindPopup(`<strong>${fullPath}</strong>`);
    });
  } else {
    console.log(`Invalid coordinates for ${locationName}`);
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
