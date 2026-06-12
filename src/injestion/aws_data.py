import requests
import os, sys
current = os.path.dirname(__file__)
path_to_root = os.path.join (current, '../..')
abs_path = os.path.abspath(path_to_root)
sys.path.append(abs_path)
import config
import utils
from minio.error import S3Error
import logging

def get_index_page():

    response = requests.get(
        config.PROVIDERS.get("aws").get("base_url") + 
        config.PROVIDERS.get("aws").get("index_extension")
        )


    if response.status_code == 200:
        return response.json()
    else:
        logging.warning (f"Error during data fetch: {response.status_code}")
        return None
    


def service_injestion(data, client):

    for key, value in data.get("offers").items():
    #Here the key is the service name and the value is the dict that has the info

        current_url_extension = value.get("currentVersionUrl")

        #If value is None -the default from .get in dict this if will be skipped
        if current_url_extension:

            full_url = config.PROVIDERS.get("aws").get("base_url") + current_url_extension
            
            logging.info(f"Streaming {key} from: {full_url}")
            try:
                with requests.get(full_url, stream=True) as fi:
                    fi.raise_for_status()

                    file_size = int(fi.headers.get('Content-Length', 0))

                    client.put_object(
                        config.PROVIDERS.get("aws").get("bucket"),
                        key + ".json", 
                        fi.raw, 
                        length=file_size,
                        content_type='application/json'
                        )
                    
            except S3Error as e:
                logging.error (f"Error: {key}, {e}")

            except Exception as e:
                logging.error (f"Error: {key}, {e}")



def main():

    utils.set_up_logger()
    logging.info ("Starting aws data injestion")

    try:
        client = config.create_minio_client()
        logging.info ("Succesfully created client")

        if utils.bucket_creation(client, config.PROVIDERS.get("aws").get("bucket")):
            data = get_index_page()
            
            if data is None:
                logging.error ("Skipping aws injestion due to index error")
                return

            service_injestion(data=data, client=client)

            logging.info ("Aws data injestion finished")

    except Exception as e:
        logging.error (f"Error occured: {e}")



if __name__ == "__main__":
    main()