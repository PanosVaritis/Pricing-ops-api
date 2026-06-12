import requests
from minio.error import S3Error
import json
import io
import os, sys
current = os.path.dirname(__file__)
path_to_root = os.path.join (current, '../..')
abs_path = os.path.abspath(path_to_root)
sys.path.append(abs_path)
import config
import utils
import logging


def service_injestion (client):

    file_counter = 1
    azure_url = config.PROVIDERS.get("azure").get("url")

    while azure_url:
        logging.info (f"Fetching page {file_counter} from {azure_url}")

        try:

            response = requests.get(azure_url)

            if response.status_code == 200:
                data = response.json()

                json_data = json.dumps(data).encode('utf-8')
                data_stream = io.BytesIO(json_data)

                client.put_object(
                    config.PROVIDERS.get("azure").get("bucket"),
                    f"azure_page_{file_counter}.json",
                    data_stream,
                    length=len(json_data),
                    content_type='application/json'
                    )
            
                azure_url = data.get("NextPageLink")
                file_counter += 1

            else:
                logging.error (f"Error during data fetching: {response.status_code}")
                break

        except Exception as e:
            logging.error (f"Connection error: {e}")



def main():

    utils.set_up_logger()

    logging.info ("Starting azure data injestion")

    try:

        client = config.create_minio_client()
        logging.info ("Succesfully created client")

        if utils.bucket_creation(client, config.PROVIDERS.get("azure").get("bucket")):
        
            logging.info ("Starting injestion")
            service_injestion(client=client)

        logging.info ("Azure data injestion finished")

    except Exception as e:
        logging.error (f"Unknown error: {e}")



if __name__ == "__main__":
    main()



#     azure_url = data.get("NextPageLink")
#     print (azure_url)

#     #Take query params from azure_url
#     parsed = urlparse(azure_url)
#     params = parse_qs(parsed.query)
#     file_counter = params.get("$skip")[0]


