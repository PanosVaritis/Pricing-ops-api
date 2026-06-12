# utils.py
from minio import Minio
from minio.error import S3Error

"""
This utility function takes a minio client and a possible bucket name as arguments, and
if not exist the bucket is created and True is returned. In case of failure false is returned
"""
def bucket_creation(client : Minio, bucket_name: str) -> bool:

    if not bucket_name:
        print ("Error: No bucket name was given")
        return False
    
    try:
        if not client.bucket_exists(bucket_name):
            print(f"Bucket with name: {bucket_name} does not exist -> Creating new...")
            client.make_bucket(bucket_name)
        else:
            print(f"Bucket with name: {bucket_name} exists -> Continuing")

    except S3Error as e:
        print(f"Error during new bucket creation. Bucket name: {bucket_name}")
        print (f"Error {e}")
        return False
    
    return True