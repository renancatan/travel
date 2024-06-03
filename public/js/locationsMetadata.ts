const YOUTUBE_PATH = "https://www.youtube.com/embed/"

export enum COUNTRY {
  PH = "ph",
  BR = "br",
}

export enum REGION {
  MINDANAO = "mindanao",
  VISAYAS = "visayas",
  PARANAGUA_BAY = "paranagua_bay",
  PETAR = "petar",
}

export enum PROVINCE {
  DAVAO_DEL_SUR = "davao_del_sur",
  CEBU = "cebu",
  SP = "sp",
  MG = "mg",
  PR = "pr",
}

export enum CITY {
  DAVAO = "davao",
  CEBU = "cebu",
  ELDORADO = "eldorado",
  GUARAQUECABA = "guaraquecaba",
  IPORANGA = "iporanga",
}

export enum CATEGORY {
  BEACHES = "beaches",
  BARS = "bars",
  CAVES = "caves",
  FALLS = "falls",
  BOAT = "boat",
  GENERAL = "general",
}

export enum PLACE {
  RESERVE_SEBUI = "reserve_sebui",
}

// Define coordinates for each location
export const COORDINATES: { [key in CITY]: [number, number] } = {
  [CITY.DAVAO]: [7.1907, 125.4553],
  [CITY.CEBU]: [10.3157, 123.8854],
  [CITY.ELDORADO]: [-24.6353, -48.4029],
  [CITY.GUARAQUECABA]: [-25.2996, -48.3444],
  [CITY.IPORANGA]: [-24.5350, -48.7046],
};

export const PLACES_COORDINATES: { [key in PLACE]: [number, number] } = {
  [PLACE.RESERVE_SEBUI]: [-25.2881, -48.2249],
};

export const VIDEO_LINKS: { [key in string]: string[] } = {
  "davao_bars_bar_name": [
    "https://www.youtube.com/embed/MzQuNihTZOY",
    "https://www.youtube.com/embed/another_video_id",
  ],
  "davao_beaches_beach_a": [
    "https://www.youtube.com/embed/video_id2",
    "https://www.youtube.com/embed/another_video_id2",
  ],

  "caverna_diabo": [
    `${YOUTUBE_PATH}8OF32kbAFK0`,
    `${YOUTUBE_PATH}JinYXmNVUdQ`,
    `${YOUTUBE_PATH}TPLQ2bT9Exs`,
    `${YOUTUBE_PATH}bW-VGz-wVl8`,
    `${YOUTUBE_PATH}VQiI1aOkzac`,
    `${YOUTUBE_PATH}4Fxj5zAH6tY`,
    `${YOUTUBE_PATH}oPTTFTpD6WM`,
    `${YOUTUBE_PATH}ljkEgGai__8`,
    `${YOUTUBE_PATH}1VMZokc3NPM`,
  ],

  "petar_caves": [
    `${YOUTUBE_PATH}`,
    `${YOUTUBE_PATH}`,
  ],

  "reserve_sebui": [
    `${YOUTUBE_PATH}u6Uhz8JNkhc`,
    `${YOUTUBE_PATH}OULfXMA5IFo`,
    `${YOUTUBE_PATH}gBOwOa5T3gA`,
  ],

  "boat1": [
    `${YOUTUBE_PATH}5k_7diqrclc`,
    `${YOUTUBE_PATH}D5OqMWPr-6I`,
    `${YOUTUBE_PATH}mOjRHqZJ8oc`,
    `${YOUTUBE_PATH}2mF8YHLEjXY`,
    `${YOUTUBE_PATH}GX2o87QDHMk`,
    `${YOUTUBE_PATH}Qn6vVugfGdA`,
    `${YOUTUBE_PATH}-feLkORk1b8`,
    `${YOUTUBE_PATH}8E7lIvch5hM`,
  ],
};