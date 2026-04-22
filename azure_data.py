import requests
from minio import Minio
from minio.error import S3Error
import json
from urllib.parse import urlparse, parse_qs
import config
from pathlib import Path

client = config.create_minio_client()

try:
    if not client.bucket_exists(config.PROVIDERS["azure"]["bucket"]):
        print("Bucket does not exist -> Creating new")
        client.make_bucket(config.PROVIDERS["azure"]["bucket"])

except S3Error as e:
    print("Error:", e)
    exit()


response = requests.get(config.PROVIDERS["azure"]["url"])


if response.status_code == 200:
    data = response.json() 
else:
    print("Error during data fetch:", {response.status_code})
    exit()


file_counter = 0
file_name = f'{config.PROVIDERS["azure"]["path"]}/azure_pricing_data_{file_counter}.json'

try:
    with open(file_name, 'w') as fi:
        json.dump(data, fi)
    
    client.fput_object(config.PROVIDERS["azure"]["bucket"], Path(file_name).name, file_name)  #The first file name is the name that the file will have in minio and the second in the name locally

except S3Error as e:
    print("Error:",e)

except Exception as e:
    print("Error:",e)


#For debug purposes
print (config.PROVIDERS["azure"]["url"])

while (data.get("NextPageLink")):

    azure_url = data.get("NextPageLink")
    print (azure_url)

    #Take query params from azure_url
    parsed = urlparse(azure_url)
    params = parse_qs(parsed.query)
    file_counter = params.get("$skip")[0]


    response = requests.get(azure_url)

    if response.status_code == 200:
        data = response.json ()
    else:
        print ("Error when trying to fetch data")

    file_name = f'{config.PROVIDERS["azure"]["path"]}/azure_pricing_data_{file_counter}.json'

    try :
        with open (file_name, "w") as fi:
            json.dump(data, fi)

        client.fput_object(config.PROVIDERS["azure"]["bucket"], Path(file_name).name, file_name)  #The first file name is the name that the file will have in minio and the second in the name locally
    
    except S3Error as e:
        print ("Error:",e)
    
    except Exception as e:
        print ("Error:", e)

