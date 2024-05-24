// generateMetadata.ts
import * as fs from 'fs';
import * as path from 'path';
import { COUNTRY, REGION, PROVINCE, CITY, CATEGORY } from './locationsMetadata.js';

interface Location {
    country: COUNTRY;
    region?: REGION;
    province: PROVINCE;
    city: CITY;
    coordinates: [number, number];
    categories: CATEGORY[];
    images: string[];
}

const metadata: Location[] = [];

function addLocation(
    country: COUNTRY,
    province: PROVINCE,
    city: CITY,
    coordinates: [number, number],
    categories: CATEGORY[],
    images: string[] = [],
    region?: REGION
) {
    const location: Location = { country, province, city, coordinates, categories, images };
    if (region) {
        location.region = region;
    }
    metadata.push(location);
}

function saveMetadata(filePath: string) {
    fs.writeFileSync(filePath, JSON.stringify(metadata, null, 2), 'utf8');
}

addLocation(COUNTRY.BR, PROVINCE.SP, CITY.ELDORADO, [-24.5281, -48.1104], [CATEGORY.CAVES]);
addLocation(COUNTRY.PH, PROVINCE.DAVAO_DEL_SUR, CITY.DAVAO, [7.1907, 125.4553], [CATEGORY.BEACHES, CATEGORY.BARS], [], REGION.MINDANAO);
addLocation(COUNTRY.PH, PROVINCE.DAVAO_DEL_SUR, CITY.DAVAO, [7.0914, 125.6109], [CATEGORY.CAVES], [], REGION.MINDANAO);
addLocation(COUNTRY.PH, PROVINCE.CEBU, CITY.CEBU, [10.3157, 123.8854], [CATEGORY.BEACHES], [], REGION.VISAYAS);

const outputFilePath = path.join(process.cwd(), 'metadata.json');
saveMetadata(outputFilePath);
