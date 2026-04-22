import requests
from config import PROVIDERS
import json


response = requests.get(PROVIDERS["aws"]["base_url"] + PROVIDERS["aws"]["index_extension"])


if response.status_code == 200:
    data = response.json()
else:
    print ("Error during data fetch:", response.status_code)
    exit()


base_file_name = PROVIDERS["aws"]["path"] + "/index.json"


try:
    with open(base_file_name, 'w') as fi:
        json.dump(data, fi)
except Exception as e:
    print(e)


