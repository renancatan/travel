import * as fs from 'fs';
import * as path from 'path';
import { COUNTRY, REGION, PROVINCE, CITY, CATEGORY, COORDINATES, PLACE, PLACES_COORDINATES, VIDEO_LINKS } from './locationsMetadata';


interface Location {
    id: string;
    country: COUNTRY;
    region?: REGION;
    province: PROVINCE;
    city: CITY;
    coordinates: [number, number];
    categories: CATEGORY[];
    images: string[];
    videos: string[];
    name: string;
}

const metadata: Location[] = [];

function addLocation(
    id: string,
    country: COUNTRY,
    province: PROVINCE,
    city: CITY,
    coordinates: [number, number],
    categories: CATEGORY[],
    images: string[] = [],
    videos: string[] = [],
    name: string,
    region?: REGION
) {
    const location: Location = { id, country, province, city, coordinates, categories, images, videos, name };
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
    'loc1',
    COUNTRY.PH,
    PROVINCE.DAVAO_DEL_SUR,
    CITY.DAVAO,
    COORDINATES[CITY.DAVAO],
    [CATEGORY.GENERAL, CATEGORY.BARS],
    ["davao_general_1.png", "davao_general_2.jpg", "davao_general_3.jpg", "davao_general_4.jpg"],
    ["https://www.youtube.com/embed/example1"],
    'Davao City Center',
    REGION.MINDANAO
);

addLocation(
    'SEBUI NATURAL RESERVE - BOAT TRAVEL',
    COUNTRY.BR,
    PROVINCE.PR,
    CITY.GUARAQUECABA,
    PLACES_COORDINATES[PLACE.RESERVE_SEBUI],
    [CATEGORY.BOAT],
    [],
    VIDEO_LINKS.reserve_sebui,
    'reserve_sebui',
    REGION.PARANAGUA_BAY
);

addLocation(
    'BOAT TRAVEL - 01',
    COUNTRY.BR,
    PROVINCE.PR,
    CITY.GUARAQUECABA,
    COORDINATES[CITY.GUARAQUECABA],
    [CATEGORY.BOAT],
    [],
    VIDEO_LINKS.boat1,
    'boat1',
    REGION.PARANAGUA_BAY
);

addLocation(
    'xx',
    COUNTRY.PH,
    PROVINCE.DAVAO_DEL_SUR,
    CITY.DAVAO,
    [7.1917, 125.453],
    [CATEGORY.BARS],
    [],
    ["https://www.youtube.com/embed/MzQuNihTZOY"],
    'bar_name',
    REGION.MINDANAO
);

addLocation(
    'subloc2',
    COUNTRY.PH,
    PROVINCE.DAVAO_DEL_SUR,
    CITY.DAVAO,
    [7.192, 125.456],
    [CATEGORY.BARS],
    [],
    [],
    'Bar B',
    REGION.MINDANAO
);

addLocation(
    'DEVIL CAVE',
    COUNTRY.BR,
    PROVINCE.SP,
    CITY.ELDORADO,
    COORDINATES[CITY.ELDORADO],
    [CATEGORY.CAVES],
    [],
    VIDEO_LINKS.caverna_diabo,
    'caverna_diabo',
);

addLocation(
    'PETAR',
    COUNTRY.BR,
    PROVINCE.SP,
    CITY.IPORANGA,
    COORDINATES[CITY.IPORANGA],
    [CATEGORY.CAVES],
    [],
    [],
    'petar_caves',
    REGION.PETAR
);


addLocation(
    'loc4',
    COUNTRY.PH,
    PROVINCE.CEBU,
    CITY.CEBU,
    COORDINATES[CITY.CEBU],
    [CATEGORY.BEACHES],
    ["cebu_beach_1.png", "cebu_beach_2.jpg"],
    ["https://www.youtube.com/embed/example3"],
    'Cebu Beach',
    REGION.VISAYAS
);

const outputFilePath = path.join(process.cwd(), 'public/js/metadata.json');
console.log("ACCESSING: metadata.json path", outputFilePath);
saveMetadata(outputFilePath);


// Verify why coordinates like iporanga are being lost when carried to json file
// upload the other videos for petar and devils cave
// more than one category is bugging the path created here (not in r2) it adds more categories to the path, eg: boat;caves for the same location
