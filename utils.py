from minio import Minio
from minio.error import S3Error
import logging
import config
import pandas as pd

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



"""
This method extacts the unique services from Minio (serviceName from azure raw data).
Its use is important so we can locate the ones we need and proceed with the EDA
"""
def find_service_name ():

    set_up_logger()
    logging.info ("Logger created, proceeding with client")
    
    client = config.create_minio_client()
    logging.info ("Succesfully created minio client")


    service_set = set()

    objects = client.list_objects(config.PROVIDERS.get("azure").get("bucket"))

    for obj in objects:
        logging.info (f"Proccesing object: {obj.object_name}")

        response = client.get_object(config.PROVIDERS.get("azure").get("bucket"), obj.object_name)

        try:
            df = pd.read_json(response)
            df_flat = pd.json_normalize(df["Items"])

            if 'serviceName' in df_flat.columns:
                services = df_flat['serviceName'].dropna().unique()
                service_set.update(services)

        finally:
            response.close()
            response.release_conn()

    logging.info(f"In tolal {len(service_set)} services were found")

    for service in service_set:
        logging.info(service)

    logging.info (service_set)


def main():
    find_service_name()

if __name__ == "__main__":
    main()



