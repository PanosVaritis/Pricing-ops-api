from minio import Minio
from minio.error import S3Error
import logging

"""
This utility function takes a minio client and a possible bucket name as arguments, and
if not exist the bucket is created and True is returned. In case of failure false is returned
"""
def bucket_creation(client : Minio, bucket_name: str) -> bool:

    if not bucket_name:
        logging.error ("Error: No bucket name was given")
        return False
    
    try:
        if not client.bucket_exists(bucket_name):
            logging.info(f"Bucket with name: {bucket_name} does not exist -> Creating new...")
            client.make_bucket(bucket_name)
        else:
            logging.info(f"Bucket with name: {bucket_name} exists -> Continuing")

    except S3Error as e:
        logging.error (f"Error during new bucket creation. Bucket name: {bucket_name}")
        logging.error (f"Error {e}")
        return False
    
    return True


 
"""
Setting up the logger. If already created then is ignored
Prints only in terminal for the time being
"""

def set_up_logger():

    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] (%(filename)s): %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            handlers=[
                logging.StreamHandler()
            ]
        )
        logging.info("Logger initialized and activated.")