"use strict";
var _a, _b;
Object.defineProperty(exports, "__esModule", { value: true });
exports.VIDEO_LINKS = exports.PLACES_COORDINATES = exports.COORDINATES = exports.PLACE = exports.CATEGORY = exports.CITY = exports.PROVINCE = exports.REGION = exports.COUNTRY = void 0;
var YOUTUBE_PATH = "https://www.youtube.com/embed/";
var COUNTRY;
(function (COUNTRY) {
    COUNTRY["PH"] = "ph";
    COUNTRY["BR"] = "br";
})(COUNTRY || (exports.COUNTRY = COUNTRY = {}));
var REGION;
(function (REGION) {
    REGION["MINDANAO"] = "mindanao";
    REGION["VISAYAS"] = "visayas";
    REGION["PARANAGUA_BAY"] = "paranagua_bay";
    REGION["PETAR"] = "petar";
})(REGION || (exports.REGION = REGION = {}));
var PROVINCE;
(function (PROVINCE) {
    PROVINCE["DAVAO_DEL_SUR"] = "davao_del_sur";
    PROVINCE["CEBU"] = "cebu";
    PROVINCE["SP"] = "sp";
    PROVINCE["MG"] = "mg";
    PROVINCE["PR"] = "pr";
})(PROVINCE || (exports.PROVINCE = PROVINCE = {}));
var CITY;
(function (CITY) {
    CITY["DAVAO"] = "davao";
    CITY["CEBU"] = "cebu";
    CITY["ELDORADO"] = "eldorado";
    CITY["GUARAQUECABA"] = "guaraquecaba";
    CITY["IPORANGA"] = "iporanga";
})(CITY || (exports.CITY = CITY = {}));
var CATEGORY;
(function (CATEGORY) {
    CATEGORY["BEACHES"] = "beaches";
    CATEGORY["BARS"] = "bars";
    CATEGORY["CAVES"] = "caves";
    CATEGORY["FALLS"] = "falls";
    CATEGORY["BOAT"] = "boat";
    CATEGORY["GENERAL"] = "general";
})(CATEGORY || (exports.CATEGORY = CATEGORY = {}));
var PLACE;
(function (PLACE) {
    PLACE["RESERVE_SEBUI"] = "reserve_sebui";
})(PLACE || (exports.PLACE = PLACE = {}));
// Define coordinates for each location
exports.COORDINATES = (_a = {},
    _a[CITY.DAVAO] = [7.1907, 125.4553],
    _a[CITY.CEBU] = [10.3157, 123.8854],
    _a[CITY.ELDORADO] = [-24.6353, -48.4029],
    _a[CITY.GUARAQUECABA] = [-25.2996, -48.3444],
    _a[CITY.IPORANGA] = [-24.5350, -48.7046],
    _a);
exports.PLACES_COORDINATES = (_b = {},
    _b[PLACE.RESERVE_SEBUI] = [-25.2881, -48.2249],
    _b);
exports.VIDEO_LINKS = {
    "davao_bars_bar_name": [
        "https://www.youtube.com/embed/MzQuNihTZOY",
        "https://www.youtube.com/embed/another_video_id",
    ],
    "davao_beaches_beach_a": [
        "https://www.youtube.com/embed/video_id2",
        "https://www.youtube.com/embed/another_video_id2",
    ],
    "caverna_diabo": [
        "".concat(YOUTUBE_PATH, "8OF32kbAFK0"),
        "".concat(YOUTUBE_PATH, "JinYXmNVUdQ"),
        "".concat(YOUTUBE_PATH, "TPLQ2bT9Exs"),
        "".concat(YOUTUBE_PATH, "bW-VGz-wVl8"),
        "".concat(YOUTUBE_PATH, "VQiI1aOkzac"),
        "".concat(YOUTUBE_PATH, "4Fxj5zAH6tY"),
        "".concat(YOUTUBE_PATH, "oPTTFTpD6WM"),
        "".concat(YOUTUBE_PATH, "ljkEgGai__8"),
        "".concat(YOUTUBE_PATH, "1VMZokc3NPM"),
    ],
    "petar_caves": [
        "".concat(YOUTUBE_PATH),
        "".concat(YOUTUBE_PATH),
    ],
    "reserve_sebui": [
        "".concat(YOUTUBE_PATH, "u6Uhz8JNkhc"),
        "".concat(YOUTUBE_PATH, "OULfXMA5IFo"),
        "".concat(YOUTUBE_PATH, "gBOwOa5T3gA"),
    ],
    "boat1": [
        "".concat(YOUTUBE_PATH, "5k_7diqrclc"),
        "".concat(YOUTUBE_PATH, "D5OqMWPr-6I"),
        "".concat(YOUTUBE_PATH, "mOjRHqZJ8oc"),
        "".concat(YOUTUBE_PATH, "2mF8YHLEjXY"),
        "".concat(YOUTUBE_PATH, "GX2o87QDHMk"),
        "".concat(YOUTUBE_PATH, "Qn6vVugfGdA"),
        "".concat(YOUTUBE_PATH, "-feLkORk1b8"),
        "".concat(YOUTUBE_PATH, "8E7lIvch5hM"),
    ],
};
