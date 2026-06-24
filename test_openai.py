import requests

try:
    response = requests.get("https://api.openai.com/v1/models")
    print(f"Status Code: {response.status_code}")
except Exception as e:
    print(f"Error: {e}")