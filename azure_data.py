import requests
from minio import Minio
from minio.error import S3Error
import json
from urllib.parse import urlparse, parse_qs

path = "/home/panos-varitis/rerl/uni/ptyxiaki/apiexamples/stored_files"



url = "https://prices.azure.com/api/retail/prices"


# client = Minio(
#     "172.18.0.2:9000", 
#     access_key="panos", 
#     secret_key="panosvaritis2003", 
#     secure=False,  
# )


# bucket = "azure"


# try:
#     if not client.bucket_exists(bucket):
#         print("Bucket does not exist -> Creating new")
#         client.make_bucket(bucket)

# except S3Error as e:
#     print("Error:", e)
#     exit()


response = requests.get(url)


if response.status_code == 200:
    data = response.json() 
else:
    print("Error during data fetch:", {response.status_code})
    exit()


# file_counter = 0
# file_name = f'{path}/azure_pricing_data_{file_counter}.json'

# try:
#     with open(file_name, 'w') as fi:
#         json.dump(data, fi)
    
#     client.fput_object(bucket, file_name, file_name)  #The first file name is the name that the file will have in minio and the second in the name locally

# except S3Error as e:
#     print("Error:",e)

# except Exception as e:
#     print("Error:",e)


#For debug purposes
print (url)

# while (data.get("NextPageLink")):
# 
#     url = data.get("NextPageLink")
#     print (url)
# 
#     #Take query params from url
#     parsed = urlparse(url)
#     params = parse_qs(parsed.query)
#     file_counter = params.get("$skip")[0]
# 
# 
#     response = requests.get(url)

#     if response.status_code == 200:
#         data = response.json ()
#     else:
#         print ("Error when trying to fetch data")
# 
#     file_name = f'{path}/azure_pricing_data_{file_counter}.json'

#     with open (file_name, "w") as fi:
#         json.dump(data, fi)





