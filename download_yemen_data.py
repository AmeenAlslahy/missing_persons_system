import urllib.request
import json
import ssl

ssl._create_default_https_context = ssl._create_unverified_context

urls = [
    "https://raw.githubusercontent.com/YemenOpenSource/Yemen-info/master/yemen-info.json",
    "https://raw.githubusercontent.com/yemen-dev/yemen-geographic-data/master/json/yemen_data.json",
    "https://raw.githubusercontent.com/alkuhlani/Yemen-JSON-Map/master/yemen.json"
]

for url in urls:
    try:
        print(f"Trying {url}...")
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = response.read()
            with open('yemen_data.json', 'wb') as f:
                f.write(data)
            print("SUCCESS!")
            break
    except Exception as e:
        print(f"Failed: {e}")
