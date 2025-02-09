import requests
import numpy as np 
from geopy.distance import geodesic

def get_nearby_businesses(latitude, longitude, radius=1000):
    """
    Fetches nearby businesses of multiple types using OpenStreetMap's Overpass API.

    :param latitude: Latitude of the location.
    :param longitude: Longitude of the location.
    :param business_types: List of business types (OSM tags like 'fast_food', 'restaurant', 'convenience').
    :param radius: Search radius in meters (default: 1000m).
    :return: List of businesses with name, address, type, latitude, and longitude.
    """
    business_types = ["fast_food", "restaurant", "convenience"]  # Modify based on OSM tags
    encodings = {"fast_food": "0", "restaurant": "1", "convenience": "2"}
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    # Build Overpass Query for multiple business types
    query_parts = []
    for business_type in business_types:
        if business_type in ["fast_food", "restaurant"]:  # These are categorized under "amenity"
            query_parts.append(f'node["amenity"="{business_type}"](around:{radius},{latitude},{longitude});')
            query_parts.append(f'way["amenity"="{business_type}"](around:{radius},{latitude},{longitude});')
            query_parts.append(f'relation["amenity"="{business_type}"](around:{radius},{latitude},{longitude});')
        else:  # Stores are categorized under "shop"
            query_parts.append(f'node["shop"="{business_type}"](around:{radius},{latitude},{longitude});')
            query_parts.append(f'way["shop"="{business_type}"](around:{radius},{latitude},{longitude});')
            query_parts.append(f'relation["shop"="{business_type}"](around:{radius},{latitude},{longitude});')

    query = f"""
    [out:json];
    (
      {"".join(query_parts)}
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
        tags = element.get("tags", {})
        name = tags.get("name", "Unknown Name")
        address = tags.get("addr:street", "Unknown Address")
        business_type = tags.get("amenity", tags.get("shop", "Unknown Type"))  # Detect type from OSM tags
        lat = element.get("lat", element.get("center", {}).get("lat"))  # Latitude
        lon = element.get("lon", element.get("center", {}).get("lon"))  # Longitude
        dist = geodesic((latitude,longitude),(lat,lon)).miles # Distance in meters
        
        # print(dist)
        businesses.append({
            "name": name,
            "address": address,
            "type": business_type,
            "latitude": lat,
            "longitude": lon,
            "distance": dist
        })
    # print(data["elements"][0])
    return businesses


if __name__ == "__main__":
    # Example Usage:
    LATITUDE = 44.9778   # Example: Minneapolis, MN
    LONGITUDE = -93.2650
    BUSINESS_TYPES = ["fast_food", "restaurant", "convenience"]  # Modify based on OSM tags
    RADIUS = 500  # Search within 1000 meters

    businesses = get_nearby_businesses(LATITUDE, LONGITUDE, BUSINESS_TYPES, RADIUS)
    for i, business in enumerate(businesses, 1):
        print(f"{i}. {business['name']} - {business['address']} (Type: {business['type']})")
        print(f"   Location: {business['latitude']}, {business['longitude']}\n")
