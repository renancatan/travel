import * as fs from 'fs';
import * as path from 'path';
import { COUNTRY, REGION, PROVINCE, CITY, CATEGORY, COORDINATES, VIDEO_LINKS } from './locationsMetadata';

interface SubLocation {
    name: string;
    coordinates: [number, number];
    images: string[];
    videos: string[];
    category: CATEGORY;
}

interface Location {
    country: COUNTRY;
    region?: REGION;
    province: PROVINCE;
    city: CITY;
    coordinates: [number, number];
    categories: CATEGORY[];
    images: string[];
    videos: string[];
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
    videos: string[] = [],
    subLocations?: SubLocation[],
    region?: REGION
) {
    const location: Location = { country, province, city, coordinates, categories, images, videos, subLocations };
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

addLocation(
    COUNTRY.PH, 
    PROVINCE.DAVAO_DEL_SUR, 
    CITY.DAVAO, 
    COORDINATES[CITY.DAVAO], 
    [CATEGORY.GENERAL, CATEGORY.BARS], 
    [], 
    [], 
    [
        { name: "bar_name", coordinates: [7.1917, 125.4530], images: [], videos: VIDEO_LINKS["davao_bars_bar_name"], category: CATEGORY.BARS },
        { name: "Bar B", coordinates: [7.1920, 125.4560], images: [], videos: [], category: CATEGORY.BARS }
    ], 
    REGION.MINDANAO
);

addLocation(
    COUNTRY.PH, 
    PROVINCE.DAVAO_DEL_SUR, 
    CITY.DAVAO, 
    [7.2100, 125.4800], 
    [CATEGORY.GENERAL, CATEGORY.BEACHES], 
    [], 
    [], 
    [
        { name: "Beach A", coordinates: [7.2110, 125.4810], images: [], videos: VIDEO_LINKS["davao_beaches_beach_a"], category: CATEGORY.BEACHES },
        { name: "Beach B", coordinates: [7.2120, 125.4850], images: [], videos: [], category: CATEGORY.BEACHES },
        { name: "general_area1", coordinates: [7.2100, 125.4800], images: [], videos: [], category: CATEGORY.GENERAL }
    ], 
    REGION.MINDANAO
);

addLocation(
    COUNTRY.PH, 
    PROVINCE.DAVAO_DEL_SUR, 
    CITY.DAVAO, 
    [7.2300, 125.5000], 
    [CATEGORY.GENERAL], 
    [], 
    [], 
    [
        { name: "general_area2", coordinates: [7.2300, 125.5000], images: [], videos: [], category: CATEGORY.GENERAL }
    ], 
    REGION.MINDANAO
);

addLocation(COUNTRY.PH, PROVINCE.CEBU, CITY.CEBU, COORDINATES[CITY.CEBU], [CATEGORY.BEACHES], [], [], [], REGION.VISAYAS);

const outputFilePath = path.join(process.cwd(), 'public/js/metadata.json');
console.log("ACCESSING: metadata.json path", outputFilePath);
saveMetadata(outputFilePath);
