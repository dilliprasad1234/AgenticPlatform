import requests

login_url = "https://example.com/login"

payload = {
    "username": "your_username",
    "password": "your_password"
}

session = requests.Session()

response = session.post(login_url, data=payload)

if response.status_code == 200:
    print("Login request successful")

    # Access an authenticated page
    dashboard = session.get("https://example.com/dashboard")
    print(dashboard.text[:500])
else:
    print("Login failed")
