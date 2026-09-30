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

def generate_image(hobby):
    try:
        response = client.images.generate(
            model="gpt-image-2.5-sunburst-2026-09-08",
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
    steam_input = request.form.get("steam_id", "").strip()

    if steam_input:
        try:
            steam_games = get_steam_games(steam_input)

            if not steam_games:
                raise ValueError("No games were found on this Steam profile.")

            if games:
                games += "\n"

            games += "\n".join(steam_games)

        except Exception as error:
            print("Steam error:", error)
            return render_template(
                "index.html",
                error=f"Could not retrieve Steam games: {error}"
            )
    location = request.form.get("location", "").strip()
    indoor = request.form.get("indoor", "Either")
    social = request.form.get("social", "Small groups")
    budget = request.form.get("budget", "Flexible")
    activity = request.form.get("activity", "Any")
    experience = request.form.get("experience", "Beginner")
    radius = int(request.form.get("radius", 100))

    if not games:
        return render_template(
            "index.html",
            error="Please enter your favorite games"
        )

    radius = radius if radius in [100, 1000, 5000, 10000] else 100

    try:
        completion = client.chat.completions.create(
            model="gpt-6-luna",
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

            hobby["image"] = generate_image(hobby["hobby_name"])

        data["radius"] = radius
        data["games"] = games

        return render_template("destination.html", data=data)

    except Exception as error:
        print("Error:", error)
        return render_template(
            "index.html",
            error="Something went wrong. Please try again."
        )

def get_steam_games(steam_input):
    api_key = os.getenv("STEAM_API_KEY")

    if not api_key:
        raise ValueError("Steam API key is missing from .env")

    steam_input = steam_input.strip()
    steam_id = None

    # Accept a 17-digit Steam ID
    if re.fullmatch(r"\d{17}", steam_input):
        steam_id = steam_input

    # Accept Steam profile URLs
    elif "steamcommunity.com" in steam_input:
        match = re.search(r"/profiles/(\d{17})", steam_input)

        if match:
            steam_id = match.group(1)
        else:
            match = re.search(r"/id/([^/?]+)", steam_input)

            if match:
                vanity_name = match.group(1)

                response = requests.get(
                    "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/",
                    params={
                        "key": api_key,
                        "vanityurl": vanity_name
                    },
                    timeout=15
                )
                response.raise_for_status()
                result = response.json()["response"]

                if result.get("success") != 1:
                    raise ValueError("Steam profile could not be found")

                steam_id = result["steamid"]

    if not steam_id:
        raise ValueError(
            "Enter a valid Steam ID or Steam profile URL"
        )

    # Retrieve the user's owned games
    response = requests.get(
        "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/",
        params={
            "key": api_key,
            "steamid": steam_id,
            "include_appinfo": True,
            "include_played_free_games": True
        },
        timeout=15
    )
    response.raise_for_status()

    result = response.json().get("response", {})
    games = result.get("games")

    if games is None:
        raise ValueError(
            "Steam did not return a game library. "
            "Check that your Game details privacy is Public."
        )

    return [
        f"{game.get('name', 'Unknown game')} "
        f"({round(game.get('playtime_forever', 0) / 60)} hours)"
        for game in games
        if game.get("name")
    ]

if __name__ == "__main__":
    app.run(debug=True)