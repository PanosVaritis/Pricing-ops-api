#Using the minio python client
from minio import Minio
from minio.error import S3Error
import os
from dotenv import load_dotenv

load_dotenv() #Reads variables from an .env and sets them in os

client = Minio(
    "172.18.0.2:9000", 
    access_key= os.getenv("MINIO_ROOT_USE", "default"), 
    secret_key= os.getenv("MINIO_ROOT_PASSWORD","DEFAULT"), 
    secure=False,  
)

#Dummy call to check if the credentials are valid  
try: 
    buckets = client.list_buckets()
    print (buckets)

except S3Error as e:
    print ("Error", e.code)


bucket = "azure"

path = "/home/panos-varitis/rerl/uni/ptyxiaki/apiexamples/stored_files"

azure_url = "https://prices.azure.com/api/retail/prices"







































# print (client.bucket_exists(bucket))
# client.make_bucket("azure")
# client.fput_object("azure", "req.txt","/home/panos-varitis/rerl/uni/ptyxiaki/code/requirements.txt")

#Remove bucket
# client.remove_bucket("panos") #Will work only if the bucket is empty. Otherwise s3 error

# try:
#     client.remove_bucket("azure") #Will work only if the bucket is empty. Otherwise s3 error
# except S3Error as e:
#     print ("error",e)

# print (client.list_buckets())

# for obj in client.list_objects("azure"):
#     print (obj._owner_name)
#     print (obj.bucket_name)
#     print (obj.object_name)
#     print (obj.last_modified)
#     print (obj.content_type)
#     client.remove_object("azure", obj.object_name)

# client.remove_bucket("azure")
