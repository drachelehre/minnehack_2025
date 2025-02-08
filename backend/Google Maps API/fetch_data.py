import requests

def get_nearby_businesses(latitude, longitude, business_type, radius=1000):
    """
    Fetches nearby businesses of a specific type using OpenStreetMap's Overpass API.

    :param latitude: Latitude of the location.
    :param longitude: Longitude of the location.
    :param business_type: Type of business (OSM tags like 'restaurant', 'cafe', 'bank', etc.).
    :param radius: Search radius in meters (default: 1000m).
    :return: List of businesses with name, address, and OSM type.
    """
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    # Overpass Query to find businesses by tag
    query = f"""
    [out:json];
    (
      node["amenity"="{business_type}"](around:{radius},{latitude},{longitude});
      way["amenity"="{business_type}"](around:{radius},{latitude},{longitude});
      relation["amenity"="{business_type}"](around:{radius},{latitude},{longitude});
    );
    out center;
    """

    response = requests.get(overpass_url, params={"data": query})
    data = response.json()

    if "elements" not in data:
        print("Error: No results found or API error")
        return []

    businesses = []
    for element in data["elements"]:
        name = element.get("tags", {}).get("name", "Unknown Name")
        address = element.get("tags", {}).get("addr:street", "Unknown Address")
        lat = element.get("lat", None)
        lon = element.get("lon", None)
        print(element)
        businesses.append({
            "name": name,
            "address": address,
            "type": business_type,
            "latitude": lat,
            "longitude": lon
            
        })

    return businesses


# Example Usage:
LATITUDE = 44.9731   # Example: Minneapolis, MN
LONGITUDE = - 93.2354
BUSINESS_TYPE = "restaurant"  # Use OSM tags like 'restaurant', 'cafe', 'bank', etc.
RADIUS = 100 # Search within 1000 meters

businesses = get_nearby_businesses(LATITUDE, LONGITUDE, BUSINESS_TYPE, RADIUS)
for i, business in enumerate(businesses, 1):
    print(f"{i}. {business['name']} - {business['latitude']} {business['longitude']} (Type: {business['type']})")
