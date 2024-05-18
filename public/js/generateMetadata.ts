import * as fs from 'fs';
import * as path from 'path';

interface Location {
    coordinates: [number, number];
    categories: string[];
}

interface Province {
    name: string;
    cities?: { [city: string]: Location };
    coordinates?: [number, number];
    categories?: string[];
}

interface Region {
    name: string;
    provinces: { [province: string]: Province };
}

interface Country {
    name: string;
    regions?: { [region: string]: Region };
    provinces?: { [province: string]: Province };
}

interface Metadata {
    countries: { [country: string]: Country };
}

const metadata: Metadata = { countries: {} };

function addLocation(
    country: string,
    province: string,
    city: string,
    coordinates: [number, number],
    categories: string[],
    region?: string
) {
    if (!metadata.countries[country]) {
        metadata.countries[country] = { name: country, regions: {}, provinces: {} };
    }

    if (region) {
        if (!metadata.countries[country].regions) {
            metadata.countries[country].regions = {};
        }
        if (!metadata.countries[country].regions[region]) {
            metadata.countries[country].regions[region] = { name: region, provinces: {} };
        }

        if (!metadata.countries[country].regions[region].provinces[province]) {
            metadata.countries[country].regions[region].provinces[province] = { name: province, cities: {} };
        }

        metadata.countries[country].regions[region].provinces[province].cities[city] = {
            coordinates: coordinates,
            categories: categories
        };
    } else {
        if (!metadata.countries[country].provinces) {
            metadata.countries[country].provinces = {};
        }
        if (!metadata.countries[country].provinces[province]) {
            metadata.countries[country].provinces[province] = { name: province, cities: {} };
        }

        metadata.countries[country].provinces[province].cities[city] = {
            coordinates: coordinates,
            categories: categories
        };
    }
}

function saveMetadata(filePath: string) {
    fs.writeFileSync(filePath, JSON.stringify(metadata, null, 2), 'utf8');
}

addLocation('br', 'sp', 'eldorado', [-24.5281, -48.1104], ['caves']);
addLocation('ph', 'davao_del_sur', 'davao', [7.1907, 125.4553], ['beaches', 'bars'], 'mindanao');
addLocation('ph', 'cebu', 'cebu', [10.3157, 123.8854], ['beaches'], 'visayas');

const outputFilePath = path.join(process.cwd(), 'metadata.json');
saveMetadata(outputFilePath);
