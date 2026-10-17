# Google Places API (New) — radius vs radiusMeters

The Places API (New) `places:searchNearby` endpoint expects:
```json
{
  "locationRestriction": {
    "circle": {
      "center": {"latitude": -25.7479, "longitude": 28.2293},
      "radius": 5000  // NOT "radiusMeters"
    }
  }
}
```

The legacy Places API used `radiusMeters`. Passing `radiusMeters` to the New endpoint returns HTTP 400 Bad Request.

Always verify: after deploying actions, run `convex run actions:fetchNearby` with a test device and confirm `Status 200` from the direct `https://places.googleapis.com/v1/places:searchNearby` call, not just a mock fallback.
