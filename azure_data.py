import requests
from minio import Minio
from minio.error import S3Error
import json
# from azure_urllib.parse import urlparse, parse_qs
from config import azure_url,path, bucket, client
from pathlib import Path

try:
    if not client.bucket_exists(bucket):
        print("Bucket does not exist -> Creating new")
        client.make_bucket(bucket)

except S3Error as e:
    print("Error:", e)
    exit()


response = requests.get(azure_url)


if response.status_code == 200:
    data = response.json() 
else:
    print("Error during data fetch:", {response.status_code})
    exit()


file_counter = 0
file_name = f'{path}/azure_pricing_data_{file_counter}.json'

try:
    with open(file_name, 'w') as fi:
        json.dump(data, fi)
    
    client.fput_object(bucket, Path(file_name).name, file_name)  #The first file name is the name that the file will have in minio and the second in the name locally

except S3Error as e:
    print("Error:",e)

except Exception as e:
    print("Error:",e)


#For debug purposes
print (azure_url)

# while (data.get("NextPageLink")):
# 
#     azure_url = data.get("NextPageLink")
#     print (azure_url)
# 
#     #Take query params from azure_url
#     parsed = azure_urlparse(url)
#     params = parse_qs(parsed.query)
#     file_counter = params.get("$skip")[0]
# 
# 
#     response = requests.get(azure_url)

#     if response.status_code == 200:
#         data = response.json ()
#     else:
#         print ("Error when trying to fetch data")
# 
#     file_name = f'{path}/azure_pricing_data_{file_counter}.json'

#     with open (file_name, "w") as fi:
#         json.dump(data, fi)

# client.remove_object("azure", "pricing_data_0.json")

    