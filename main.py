from dotenv import load_dotenv
from openai import OpenAI
from flask import Flask, request, render_template
import requests
import json
import os
import re
import base64
import math

load_dotenv()

client = OpenAI()
app = Flask(__name__)

# Free OpenStreetMap services
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

HEADERS = {
    "User-Agent": "GameToReality/1.0 hobby-discovery-project"
}


def get_location(location):
    response = requests.get(
        NOMINATIM_URL,
        params={
            "q": location,
            "format": "json",
            "limit": 1
        },
        headers=HEADERS,
        timeout=15
    )
    response.raise_for_status()
    results = response.json()

    if not results:
        return None

    return {
        "lat": float(results[0]["lat"]),
        "lon": float(results[0]["lon"]),
        "name": results[0]["display_name"]
    }


def find_places(lat, lon, radius, search_terms):
    # Search OpenStreetMap for places matching hobby-related terms.
    terms = {
        "board games": ['"shop"="games"', '"amenity"="community_centre"'],
        "tabletop games": ['"shop"="games"', '"amenity"="community_centre"'],
        "paintball": ['"sport"="paintball"', '"leisure"="sports_centre"'],
        "hiking": ['"route"="hiking"', '"leisure"="nature_reserve"'],
        "climbing": ['"sport"="climbing"', '"leisure"="sports_centre"'],
        "art": ['"craft"="art"', '"amenity"="arts_centre"'],
        "pottery": ['"craft"="pottery"', '"amenity"="arts_centre"'],
        "woodworking": ['"craft"="carpenter"', '"craft"="woodworking"'],
        "martial arts": ['"sport"="martial_arts"', '"leisure"="sports_centre"'],
        "sports": ['"leisure"="sports_centre"', '"leisure"="pitch"'],
        "photography": ['"amenity"="arts_centre"'],
        "robotics": ['"club"="robotics"', '"amenity"="community_centre"'],
        "chess": ['"club"="chess"', '"amenity"="community_centre"'],
        "theater": ['"amenity"="theatre"', '"amenity"="community_centre"'],
        "gardening": ['"leisure"="garden"', '"community_garden"="yes"'],
        "dance": ['"sport"="dance"', '"leisure"="dance"'],
        "music": ['"amenity"="music_school"', '"amenity"="arts_centre"'],
        "volunteering": ['"amenity"="community_centre"']
    }

    query_parts = []
    for term in search_terms:
        term = term.lower()
        for hobby, tags in terms.items():
            if hobby in term or term in hobby:
                for tag in tags:
                    query_parts.append(
                        f'node(around:{radius},{lat},{lon})[{tag}];'
                        f'way(around:{radius},{lat},{lon})[{tag}];'
                    )

    if not query_parts:
        return []

    query = "[out:json][timeout:20];(" + "".join(set(query_parts)) + ");out center tags;"

    try:
        response = requests.post(
            OVERPASS_URL,
            data={"data": query},
            headers=HEADERS,
            timeout=30
        )
        response.raise_for_status()
        elements = response.json().get("elements", [])
    except requests.RequestException:
        return []

    places = []
    seen = set()

    for element in elements:
        tags = element.get("tags", {})
        name = tags.get("name")

        if not name or name in seen:
            continue

        place_lat = element.get("lat", element.get("center", {}).get("lat"))
        place_lon = element.get("lon", element.get("center", {}).get("lon"))

        if place_lat is None or place_lon is None:
            continue

        distance = math.sqrt(
            ((float(place_lat) - lat) * 111320) ** 2 +
            ((float(place_lon) - lon) * 111320 *
             math.cos(math.radians(lat))) ** 2
        )

        if distance > radius:
            continue

        seen.add(name)
        places.append({
            "name": name,
            "address": ", ".join(filter(None, [
                tags.get("addr:housenumber"),
                tags.get("addr:street"),
                tags.get("addr:city")
            ])) or "Address not listed",
            "distance": round(distance),
            "type": tags.get("sport") or tags.get("shop") or
                    tags.get("leisure") or tags.get("amenity", "Activity"),
            "website": tags.get("website"),
            "lat": float(place_lat),
            "lon": float(place_lon)
        })

    return sorted(places, key=lambda p: p["distance"])[:5]


def generate_image(hobby):
    try:
        response = client.images.generate(
            model="gpt-image-1",
            prompt=(
                f"Create a colorful, welcoming, high-quality illustration "
                f"of people enjoying the real-world hobby of {hobby}. "
                "Show the actual physical activity, friendly social atmosphere, "
                "and an inviting environment. Modern editorial illustration."
            ),
            size="1024x1024",
            quality="low"
        )

        image_data = response.data[0].b64_json
        return "data:image/png;base64," + image_data

    except Exception as error:
        print("Image generation failed:", error)
        return None


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template("index.html")

    games = request.form.get("games", "").strip()
    location = request.form.get("location", "").strip()
    indoor = request.form.get("indoor", "Either")
    social = request.form.get("social", "Small groups")
    budget = request.form.get("budget", "Flexible")
    activity = request.form.get("activity", "Any")
    experience = request.form.get("experience", "Beginner")
    radius = int(request.form.get("radius", 100))

    if not games or not location:
        return render_template(
            "index.html",
            error="Please enter your favorite games and location."
        )

    radius = radius if radius in [100, 1000, 5000, 10000] else 100

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": """
                    You are Game to Reality, a friendly hobby discovery assistant.
                    Analyze games as possible indicators of interests, not fixed
                    personality traits. Recommend exactly 3 distinct offline
                    hobbies. Avoid shaming gaming. Include practical skills,
                    beginner experience, social opportunities, estimated cost,
                    and search terms for real-world locations.

                    Return valid JSON with:
                    interest_summary, identified_interests,
                    transferable_skills, recommendations.

                    recommendations must be an array of 3 objects containing:
                    hobby_name, description, why_it_matches,
                    transferable_skills, beginner_experience,
                    social_opportunities, difficulty, estimated_cost,
                    image_prompt, location_search_terms.

                    Do not invent local businesses. Do not assume users have
                    mastered skills just because they play a game.
                    """
                },
                {
                    "role": "user",
                    "content": f"""
                    Favorite games: {games}
                    Preferred setting: {indoor}
                    Social preference: {social}
                    Budget: {budget}
                    Physical activity: {activity}
                    Experience level: {experience}

                    Recommend three diverse real-world hobbies.
                    """
                }
            ]
        )

        data = json.loads(completion.choices[0].message.content)

        if not isinstance(data.get("recommendations"), list):
            raise ValueError("Invalid recommendations")

        data["recommendations"] = data["recommendations"][:3]

        # Find the user's general location
        coordinates = get_location(location)

        if not coordinates:
            return render_template(
                "index.html",
                error="We could not find that location. Try a city or ZIP code."
            )

        data["location_name"] = coordinates["name"]
        data["map_points"] = []

        for hobby in data["recommendations"]:
            terms = hobby.get("location_search_terms", [])
            if isinstance(terms, str):
                terms = [terms]

            places = find_places(
                coordinates["lat"],
                coordinates["lon"],
                radius,
                terms + [hobby.get("hobby_name", "")]
            )

            hobby["places"] = places
            hobby["image"] = generate_image(hobby["hobby_name"])

            for place in places:
                place["hobby"] = hobby["hobby_name"]
                data["map_points"].append(place)

        data["radius"] = radius
        data["games"] = games

        return render_template("destination.html", data=data)

    except Exception as error:
        print("Error:", error)
        return render_template(
            "index.html",
            error="Something went wrong. Please try again."
        )


if __name__ == "__main__":
    app.run(debug=True)