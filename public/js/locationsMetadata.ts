const YOUTUBE_PATH = "https://www.youtube.com"

export enum COUNTRY {
  PH = "ph",
  BR = "br",
}

export enum REGION {
  MINDANAO = "mindanao",
  VISAYAS = "visayas",
}

export enum PROVINCE {
  DAVAO_DEL_SUR = "davao_del_sur",
  CEBU = "cebu",
  SP = "sp",
}

export enum CITY {
  DAVAO = "davao",
  CEBU = "cebu",
  ELDORADO = "eldorado",
}

export enum CATEGORY {
  BEACHES = "beaches",
  BARS = "bars",
  CAVES = "caves",
  GENERAL = "general",
}

// Define coordinates for each location
export const COORDINATES: { [key in CITY]: [number, number] } = {
  [CITY.DAVAO]: [7.1907, 125.4553],
  [CITY.CEBU]: [10.3157, 123.8854],
  [CITY.ELDORADO]: [-24.5281, -48.1104],
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
};