import requests
from minio import Minio
from minio.error import S3Error
import json


url = "https://prices.azure.com/api/retail/prices?$skip=829000"


client = Minio(
    "172.18.0.2:9000", 
    access_key="panos", 
    secret_key="panosvaritis2003", 
    secure=False,  
)


bucket = "azure"


try:
    if not client.bucket_exists(bucket):
        print("Bucket does not exist -> Creating new")
        client.make_bucket(bucket)

except S3Error as e:
    print("Error:", e)
    exit()


response = requests.get(url)


if response.status_code == 200:
    data = response.json() 
else:
    print(f"Error during data fetch: {response.status_code}")
    exit()

file_name = 'azure_pricing_data1.json'

try:
    with open(file_name, 'w') as fi:
        json.dump(data, fi)
    
    client.fput_object(bucket, file_name, file_name)  #The first file name is the name that the file will have in minio and the second in the name locally

except S3Error as e:
    print("Error:",e)

except Exception as e:
    print("Error:",e)



# print (data['NextPageLink'])
# print (response.json())





















