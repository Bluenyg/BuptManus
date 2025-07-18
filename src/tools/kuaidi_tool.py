import os
import json
import hashlib
import requests
from langchain_core.tools import tool
from src.config import KUAIDI100_API_KEY,CUSTOMER_ID

@tool
def track_logistics(com: str, num: str, phone: str = "", ship_from: str = "", ship_to: str = "") -> str:
    """
    Queries real-time logistics tracking information for a package.

    Args:
        com (str): The courier company's code, in all lowercase (e.g., 'yuantong', 'shunfeng').
        num (str): The tracking number, with a maximum length of 32 characters.
        phone (str): The recipient's or sender's phone number. Can be the last four digits.
        ship_from (str): The origin city in 'province-city-district' format. Providing this improves accuracy.
        ship_to (str): The destination city in 'province-city-district' format. Providing this improves accuracy.

    Returns:
        str: The API response text, typically a JSON string with tracking details.
    """
    # --- Get credentials securely from environment variables ---
    api_key = KUAIDI100_API_KEY
    customer_id = CUSTOMER_ID

    if not api_key or not customer_id:
        return "Error: KUAIDI100_KEY and KUAIDI100_CUSTOMER environment variables must be set."

    url = 'https://poll.kuaidi100.com/poll/query.do'

    param = {
        'com': com,
        'num': num,
        'phone': phone,
        'from': ship_from,
        'to': ship_to,
        'resultv2': '1',  # Enable administrative area parsing
        'show': '0',      # Return format: json
        'order': 'desc'   # Sort order: descending
    }
    param_str = json.dumps(param)

    # --- Signature Generation ---
    # The signature is an MD5 hash of (param_json_string + api_key + customer_id) in uppercase.
    temp_sign = param_str + api_key + customer_id
    md = hashlib.md5()
    md.update(temp_sign.encode())
    sign = md.hexdigest().upper()

    request_data = {
        'customer': customer_id,
        'param': param_str,
        'sign': sign
    }

    # --- Send Request ---
    try:
        response = requests.post(url, data=request_data, timeout=10)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        return response.text
    except requests.exceptions.RequestException as e:
        return f"Error during API request: {e}"


# --- Test Block (Corrected) ---
if __name__ == "__main__":
    # Note: To run this test, you must have your KUAIDI100_API_KEY and CUSTOMER_ID
    # correctly set in your src/config.py file.

    print("--- Running test for track_logistics tool ---")

    # To get a successful response, replace this with a REAL, valid tracking number.
    test_com = "shunfeng"
    test_num = "SF3190621662050"
    test_phone = "18138199852"

    print(f"\nTesting with courier '{test_com}' and number '{test_num}'...")

    # --- THIS IS THE CORRECTED PART ---
    # Create a dictionary for the tool's input
    tool_input = {"com": test_com, "num": test_num,"phone":test_phone}
    # Call the tool using the .invoke() method with the input dictionary
    result = track_logistics.invoke(tool_input)

    print("API Response:")
    try:
        parsed_json = json.loads(result)
        print(json.dumps(parsed_json, indent=2, ensure_ascii=False))
    except json.JSONDecodeError:
        print(result)

    print("\n--- Test finished ---")