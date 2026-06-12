import requests
import io
import json
import sys, os
current = os.path.dirname(__file__)
path_to_root = os.path.join (current, '../..')
abs_path = os.path.abspath(path_to_root)
sys.path.append(abs_path)
import config
from minio.error import S3Error
import time
import utils
import logging


def get_services():

    services_url = (
        config.PROVIDERS.get("google").get("base_url") + 
        config.PROVIDERS.get("google").get("api_key")
    )
    response = requests.get(services_url)

    if response.status_code == 200: 
        services = response.json().get("services", [])
    else:
        logging.warning (f"Error during index data fetching: {response.status_code}")
        return []
    
    return services



#Display name is the name of the service provided. For example compute engine -We will use this for the storage-
#Name and service id can be used to retrieve the json with the skus

def service_injestion(services, client):

    for service in services:
        name = service.get("name")
        service_id = service.get("serviceId")
        service_displayName = service.get("displayName", "Unknown_Service").replace(" ", "_").replace("/", "-").replace("-", "_")

        sku_url = (
            config.PROVIDERS.get("google").get("url") + 
            service_id + 
            config.PROVIDERS.get("google").get("url_extension") +
            config.PROVIDERS.get("google").get("api_key")
            )
        

        page_counter = 1
        while sku_url:
            logging.info (sku_url)
            try:
                response = requests.get(sku_url)

                if response.status_code == 200:
                    data = response.json()
                else:
                    logging.error (f"Error during data fetch at {service_displayName} with status code {response.status_code}")
                    break #Better than exit. Continue with next service


                json_data = json.dumps(data).encode('utf-8')
                data_stream = io.BytesIO(json_data)


                object_name = f"{service_displayName}/page_{page_counter}.json"


                client.put_object(
                        config.PROVIDERS.get("google").get("bucket"),
                        object_name,
                        data_stream,
                        length=len(json_data),
                        content_type='application/json'
                        )

                token = data.get("nextPageToken")
                if token:
                    sku_url = (        
                        config.PROVIDERS.get("google").get("url") + 
                        service_id + 
                        config.PROVIDERS.get("google").get("url_extension") +
                        config.PROVIDERS.get("google").get("api_key") +
                        config.PROVIDERS.get("google").get("nextPage") +
                        token
                    )
                    page_counter += 1
                else:
                    sku_url = None

                #Sleep before next request to avoid 104 error 
                time.sleep(0.2)

            except S3Error as e:
                logging.error (f"Error: {e}")
                break #If there is a minio error the break
            except Exception as e:
                logging.error (f"Error: {e}")



def main():

    utils.set_up_logger()

    logging.info ("Starting google cloud data injestion")

    try:    

        client = config.create_minio_client()
        logging.info ("Succesfully created client")

        if not utils.bucket_creation(client, config.PROVIDERS.get("google").get("bucket")):
            return



        ser = get_services()
        if not ser:
            logging.warning ("No services found.. Skipping GCD")
            return
        
        logging.info ("Service list fetched!!")
        # We have in total len(services). 1777
        logging.info (f"Starting the injestion of the {len(ser)} services provided")

        service_injestion(services=ser, client=client)

        logging.info ("Google cloud data injestion finished")

    except Exception as e:
        logging.error (f"Unknown error: {e}")


if __name__ == "__main__":
    main()