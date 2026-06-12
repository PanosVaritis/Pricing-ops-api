#Using the minio python client
from minio import Minio
from minio.error import S3Error
import os
from dotenv import load_dotenv

def create_minio_client():
    
    load_dotenv() #Reads variables from an .env and sets them in os

    client = Minio(
        "localhost:9000", 
        access_key= os.getenv("MINIO_ROOT_USER", "default"), 
        secret_key= os.getenv("MINIO_ROOT_PASSWORD","DEFAULT"), 
        secure=False,  
    )

    try: 
        buckets = client.list_buckets()
        
        print (buckets)

    except S3Error as e:
        print ("Error", e.code)

    return client

load_dotenv()


PROVIDERS = {
    "azure": {
        "url":"https://prices.azure.com/api/retail/prices",
        "bucket":"azure",
        "clean_bucket": "azure-clean"
    },
    "aws":{
        "bucket":"aws",
        "base_url":"https://pricing.us-east-1.amazonaws.com",
        "index_extension": "/offers/v1.0/aws/index.json",
        "clean_bucket": "aws-clean"
    },
    "google":{
        "base_url":"https://cloudbilling.googleapis.com/v1/services?key=", #key=YOUR_API_KEY
        "bucket":"google",
        "api_key": os.getenv("GOOGLE_API_KEY", "default"),
        "url": "https://cloudbilling.googleapis.com/v1/services/",
        "url_extension": "/skus?key=",
        "nextPage": "&pageToken=",
        "clean_bucket": "google-clean"
    }
}


def main():
    create_minio_client()



if __name__ == "__main__":
    main()

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

    #     client.remove_object("azure", obj.object_name)

    # client.remove_bucket("azure")    
    

    # print (obj._owner_name)
    # print (obj.bucket_name)
    # print (obj.object_name)
    # print (obj.last_modified)
    # print (obj.content_type)



# import config
# client = config.create_minio_client()
# bucket_name = "gcp-prices-raw"

# # Φέρνουμε όλα τα objects μέσα στο bucket
# objects = client.list_objects(bucket_name, recursive=True)
# count = sum(1 for _ in objects)

# print(f"Πραγματικός αριθμός αρχείων στο MinIO: {count}")