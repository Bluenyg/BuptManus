import os
import json
import requests
from langchain_core.tools import tool
# from src.config import AMAP_API_KEY  # Assuming you'll store the API key in config.py


@tool
def get_weather_info(city_code: str) -> str:
    """
    Queries weather information for a specific city using AMap Weather API.

    Args:
        city_code (str): The city code (e.g., '110101' for Beijing Dongcheng District)

    Returns:
        str: The API response text, typically a JSON string with weather details.
    """
    # --- Get API key securely from environment variables ---
    AMAP_API_KEY = 'b1ca099008a4fb517e89b0c5e1016170'
    api_key = AMAP_API_KEY

    if not api_key:
        return "Error: AMAP_API_KEY environment variable must be set."

    url = 'https://restapi.amap.com/v3/weather/weatherInfo'

    params = {
        'city': city_code,
        'key': api_key,
        'extensions': 'base',  # 'base' for basic weather, 'all' for forecast
        'output': 'JSON'  # Response format
    }

    # --- Send Request ---
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.text
    except requests.exceptions.RequestException as e:
        return f"Error during API request: {e}"


# --- Test Block ---
if __name__ == "__main__":
    # Note: To run this test, you must have your AMAP_API_KEY
    # correctly set in your src/config.py file.

    print("--- Running test for get_weather_info tool ---")

    # Test with Beijing Dongcheng District code
    test_city_code = "110101"

    print(f"\nTesting with city code '{test_city_code}'...")

    # Call the tool
    tool_input = {"city_code": test_city_code}
    result = get_weather_info.invoke(tool_input)

    print("API Response:")
    try:
        parsed_json = json.loads(result)
        print(json.dumps(parsed_json, indent=2, ensure_ascii=False))
    except json.JSONDecodeError:
        print(result)

    print("\n--- Test finished ---")