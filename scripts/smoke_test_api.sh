#!/usr/bin/env bash
set -euo pipefail

API_BASE_URL="${1:-http://127.0.0.1:8000}"

echo
echo "Health check"
curl -fsS "${API_BASE_URL}/healthz"

echo
echo
echo "Runtime check"
curl -fsS "${API_BASE_URL}/runtime"

echo
echo
echo "LLM text smoke test"
curl -fsS \
  -X POST "${API_BASE_URL}/ask" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Give me 3 short caption ideas for a cave travel post.","model":"ggl2"}'

echo
echo
echo "Album create smoke test"
SMOKE_ALBUM_NAME="Smoke Test Album $(date +%s)"
ALBUM_JSON="$(curl -fsS \
  -X POST "${API_BASE_URL}/albums" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"${SMOKE_ALBUM_NAME}\",\"description\":\"Local ingestion smoke test\"}")"
printf '%s\n' "${ALBUM_JSON}"

ALBUM_ID="$(python -c 'import json,sys; print(json.loads(sys.stdin.read())["id"])' <<< "${ALBUM_JSON}")"
SMOKE_FILE="$(mktemp /tmp/travel-smoke-XXXXXX.svg)"
cat > "${SMOKE_FILE}" <<'SVG'
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1500" viewBox="0 0 1200 1500">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#165f77"/>
      <stop offset="60%" stop-color="#db7a34"/>
      <stop offset="100%" stop-color="#f4d7a1"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="1500" fill="url(#bg)"/>
  <circle cx="920" cy="260" r="160" fill="rgba(255,255,255,0.22)"/>
  <path d="M0 1180 Q260 980 510 1130 T1200 1070 L1200 1500 L0 1500 Z" fill="#0f3d4f"/>
  <path d="M0 1270 Q250 1110 540 1230 T1200 1160 L1200 1500 L0 1500 Z" fill="#1b5c60"/>
  <text x="90" y="230" fill="#fff8ee" font-size="94" font-family="Georgia, serif">Travel Project</text>
  <text x="90" y="330" fill="#fff8ee" font-size="42" font-family="Georgia, serif">Visible smoke-test artwork</text>
  <text x="90" y="1290" fill="#f6e8d0" font-size="56" font-family="Georgia, serif">Upload flow preview</text>
</svg>
SVG

echo
echo "Album upload smoke test"
curl -fsS \
  -X POST "${API_BASE_URL}/albums/${ALBUM_ID}/upload" \
  -H "Content-Type: image/svg+xml" \
  -H "X-Filename: smoke-test.svg" \
  --data-binary @"${SMOKE_FILE}"

echo
echo
echo "Album fetch smoke test"
curl -fsS "${API_BASE_URL}/albums/${ALBUM_ID}"

echo
echo
echo "AI description smoke test"
curl -fsS -X POST "${API_BASE_URL}/albums/${ALBUM_ID}/description/auto"

echo
echo
echo "Manual description update smoke test"
curl -fsS \
  -X PATCH "${API_BASE_URL}/albums/${ALBUM_ID}" \
  -H "Content-Type: application/json" \
  -d '{"description":"Manual smoke-test description after upload."}'

echo
echo
echo "AI suggestion smoke test"
curl -fsS -X POST "${API_BASE_URL}/albums/${ALBUM_ID}/suggestions"

MEDIA_ID="$(curl -fsS "${API_BASE_URL}/albums/${ALBUM_ID}" | python -c 'import json,sys; print(json.loads(sys.stdin.read())["media_items"][0]["id"])')"

echo
echo
echo "Media delete smoke test"
curl -fsS -X DELETE "${API_BASE_URL}/albums/${ALBUM_ID}/media/${MEDIA_ID}"

echo
echo
echo "Album delete smoke test"
curl -fsS -X DELETE "${API_BASE_URL}/albums/${ALBUM_ID}" -o /dev/null -w '%{http_code}\n'

rm -f "${SMOKE_FILE}"
echo
