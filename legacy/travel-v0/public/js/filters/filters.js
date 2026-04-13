export function populateFilters(locations, regionFilterId, categoryFilterId) {
  const regionFilter = document.getElementById(regionFilterId);
  const categoryFilter = document.getElementById(categoryFilterId);

  const regions = new Set();
  const categories = new Set();

  locations.forEach(location => {
    if (location.region) regions.add(location.region);
    location.categories.forEach(category => categories.add(category));
  });

  regions.forEach(region => {
    const option = document.createElement('option');
    option.value = region;
    option.text = region;
    regionFilter.appendChild(option);
  });

  categories.forEach(category => {
    const option = document.createElement('option');
    option.value = category;
    option.text = category;
    categoryFilter.appendChild(option);
  });

  console.log('Filters populated with regions:', Array.from(regions));
  console.log('Filters populated with categories:', Array.from(categories));
}

export function filterMarkers(allLocations, selectedRegion, selectedCategory, map, processLocation) {
  console.log('Filtering markers with selected region:', selectedRegion);
  console.log('Filtering markers with selected category:', selectedCategory);

  let markers = [];

  const filteredLocations = allLocations.filter(location => {
    const regionMatches = selectedRegion === 'all' || location.region === selectedRegion;
    const categoryMatches = selectedCategory === 'all' || location.categories.includes(selectedCategory);
    return regionMatches && categoryMatches;
  });

  console.log('Filtered locations:', filteredLocations);

  filteredLocations.forEach(location => {
    const marker = processLocation(location, map);
    if (marker) {
      markers.push(marker);
    }
  });

  return markers;
}
