import * as fs from 'fs';
import * as path from 'path';
import { COUNTRY, REGION, PROVINCE, CITY, CATEGORY } from './locationsMetadata.js';

interface SubLocation {
    name: string;
    coordinates: [number, number];
    images: string[];
}

interface Location {
    country: COUNTRY;
    region?: REGION;
    province: PROVINCE;
    city: CITY;
    coordinates: [number, number];
    categories: CATEGORY[];
    images: string[];
    subLocations?: SubLocation[];
}

const metadata: Location[] = [];

function addLocation(
    country: COUNTRY,
    province: PROVINCE,
    city: CITY,
    coordinates: [number, number],
    categories: CATEGORY[],
    images: string[] = [],
    subLocations?: SubLocation[],
    region?: REGION
) {
    const location: Location = { country, province, city, coordinates, categories, images, subLocations };
    if (region) {
        location.region = region;
    }
    metadata.push(location);
    console.log(`Added location: ${JSON.stringify(location, null, 2)}`);
}

function saveMetadata(filePath: string) {
    fs.writeFileSync(filePath, JSON.stringify(metadata, null, 2), 'utf8');
    console.log(`Metadata saved to ${filePath}`);
}

// Example locations with sub-locations
addLocation(
    COUNTRY.PH, 
    PROVINCE.DAVAO_DEL_SUR, 
    CITY.DAVAO, 
    [7.1907, 125.4553], 
    [CATEGORY.BARS], 
    [], 
    [
        { name: "bar_name", coordinates: [7.1917, 125.4530], images: [] },
        { name: "Bar B", coordinates: [7.1920, 125.4560], images: [] }
    ], 
    REGION.MINDANAO
);

addLocation(
    COUNTRY.PH, 
    PROVINCE.DAVAO_DEL_SUR, 
    CITY.DAVAO, 
    [7.2100, 125.4800], 
    [CATEGORY.BEACHES], 
    [], 
    [
        { name: "Beach A", coordinates: [7.2110, 125.4810], images: [] },
        { name: "Beach B", coordinates: [7.2120, 125.4850], images: [] }
    ], 
    REGION.MINDANAO
);

addLocation(
    COUNTRY.PH, 
    PROVINCE.DAVAO_DEL_SUR, 
    CITY.DAVAO, 
    [7.2300, 125.5000], 
    [], 
    [], 
    [],
    REGION.MINDANAO
);

addLocation(COUNTRY.PH, PROVINCE.CEBU, CITY.CEBU, [10.3157, 123.8854], [CATEGORY.BEACHES], [], [], REGION.VISAYAS);

const outputFilePath = path.join(process.cwd(), 'public/js/metadata.json');
console.log("ACCESSING: metadata.json path", outputFilePath)
saveMetadata(outputFilePath);
