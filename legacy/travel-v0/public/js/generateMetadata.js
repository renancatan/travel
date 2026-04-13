"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
var fs = require("fs");
var path = require("path");
var locationsMetadata_1 = require("./locationsMetadata");
var metadata = [];
function addLocation(id, country, province, city, coordinates, categories, images, videos, name, region) {
    if (images === void 0) { images = []; }
    if (videos === void 0) { videos = []; }
    var location = { id: id, country: country, province: province, city: city, coordinates: coordinates, categories: categories, images: images, videos: videos, name: name };
    if (region) {
        location.region = region;
    }
    metadata.push(location);
    console.log("Added location: ".concat(JSON.stringify(location, null, 2)));
}
function saveMetadata(filePath) {
    fs.writeFileSync(filePath, JSON.stringify(metadata, null, 2), 'utf8');
    console.log("Metadata saved to ".concat(filePath));
}
addLocation('loc1', locationsMetadata_1.COUNTRY.PH, locationsMetadata_1.PROVINCE.DAVAO_DEL_SUR, locationsMetadata_1.CITY.DAVAO, locationsMetadata_1.COORDINATES[locationsMetadata_1.CITY.DAVAO], [locationsMetadata_1.CATEGORY.GENERAL, locationsMetadata_1.CATEGORY.BARS], ["davao_general_1.png", "davao_general_2.jpg", "davao_general_3.jpg", "davao_general_4.jpg"], ["https://www.youtube.com/embed/example1"], 'Davao City Center', locationsMetadata_1.REGION.MINDANAO);
addLocation('SEBUI NATURAL RESERVE - BOAT TRAVEL', locationsMetadata_1.COUNTRY.BR, locationsMetadata_1.PROVINCE.PR, locationsMetadata_1.CITY.GUARAQUECABA, locationsMetadata_1.PLACES_COORDINATES[locationsMetadata_1.PLACE.RESERVE_SEBUI], [locationsMetadata_1.CATEGORY.BOAT], [], locationsMetadata_1.VIDEO_LINKS.reserve_sebui, 'reserve_sebui', locationsMetadata_1.REGION.PARANAGUA_BAY);
addLocation('BOAT TRAVEL - 01', locationsMetadata_1.COUNTRY.BR, locationsMetadata_1.PROVINCE.PR, locationsMetadata_1.CITY.GUARAQUECABA, locationsMetadata_1.COORDINATES[locationsMetadata_1.CITY.GUARAQUECABA], [locationsMetadata_1.CATEGORY.BOAT], [], locationsMetadata_1.VIDEO_LINKS.boat1, 'boat1', locationsMetadata_1.REGION.PARANAGUA_BAY);
addLocation('xx', locationsMetadata_1.COUNTRY.PH, locationsMetadata_1.PROVINCE.DAVAO_DEL_SUR, locationsMetadata_1.CITY.DAVAO, [7.1917, 125.453], [locationsMetadata_1.CATEGORY.BARS], [], ["https://www.youtube.com/embed/MzQuNihTZOY"], 'bar_name', locationsMetadata_1.REGION.MINDANAO);
addLocation('subloc2', locationsMetadata_1.COUNTRY.PH, locationsMetadata_1.PROVINCE.DAVAO_DEL_SUR, locationsMetadata_1.CITY.DAVAO, [7.192, 125.456], [locationsMetadata_1.CATEGORY.BARS], [], [], 'Bar B', locationsMetadata_1.REGION.MINDANAO);
addLocation('DEVIL CAVE', locationsMetadata_1.COUNTRY.BR, locationsMetadata_1.PROVINCE.SP, locationsMetadata_1.CITY.ELDORADO, locationsMetadata_1.COORDINATES[locationsMetadata_1.CITY.ELDORADO], [locationsMetadata_1.CATEGORY.CAVES], [], locationsMetadata_1.VIDEO_LINKS.caverna_diabo, 'caverna_diabo');
addLocation('PETAR', locationsMetadata_1.COUNTRY.BR, locationsMetadata_1.PROVINCE.SP, locationsMetadata_1.CITY.IPORANGA, locationsMetadata_1.COORDINATES[locationsMetadata_1.CITY.IPORANGA], [locationsMetadata_1.CATEGORY.CAVES], [], [], 'petar_caves', locationsMetadata_1.REGION.PETAR);
addLocation('loc4', locationsMetadata_1.COUNTRY.PH, locationsMetadata_1.PROVINCE.CEBU, locationsMetadata_1.CITY.CEBU, locationsMetadata_1.COORDINATES[locationsMetadata_1.CITY.CEBU], [locationsMetadata_1.CATEGORY.BEACHES], ["cebu_beach_1.png", "cebu_beach_2.jpg"], ["https://www.youtube.com/embed/example3"], 'Cebu Beach', locationsMetadata_1.REGION.VISAYAS);
var outputFilePath = path.join(process.cwd(), 'public/js/metadata.json');
console.log("ACCESSING: metadata.json path", outputFilePath);
saveMetadata(outputFilePath);
// Verify why coordinates like iporanga are being lost when carried to json file
// upload the other videos for petar and devils cave
// more than one category is bugging the path created here (not in r2) it adds more categories to the path, eg: boat;caves for the same location
