export function populateFilters(locations, regionFilterId, categoryFilterId, priceFilterId, scoreFilterId) {
    const regionFilter = document.getElementById(regionFilterId);
    const categoryFilter = document.getElementById(categoryFilterId);
    const priceFilter = document.getElementById(priceFilterId);
    const scoreFilter = document.getElementById(scoreFilterId);
  
    const regions = new Set();
    const categories = new Set();
    const prices = new Set();
  
    locations.forEach(location => {
      if (location.region) regions.add(location.region);
      location.categories.forEach(category => categories.add(category));
      if (location.prices) prices.add(parseFloat(location.prices));
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
  
    const maxPrice = Math.max(...prices) + 1;
    priceFilter.max = maxPrice;
    priceFilter.min = 0;
    priceFilter.step = 1;
    priceFilter.value = maxPrice;
    document.getElementById('priceOutput').value = maxPrice;
  
    console.log('Filters populated with regions:', Array.from(regions));
    console.log('Filters populated with categories:', Array.from(categories));
    console.log('Filters populated with price range:', 0, maxPrice);
}
