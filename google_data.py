import requests
import io
import json
import config
from minio.error import S3Error

client = config.create_minio_client()

try:
    if not client.bucket_exists(config.PROVIDERS.get("google").get("bucket")):
        print("Bucket does not exist -> Creating new")
        client.make_bucket(config.PROVIDERS.get("google").get("bucket"))

except S3Error as e:
    print("Error:", e)
    exit()


services_url = (
    config.PROVIDERS.get("google").get("base_url") + 
    config.PROVIDERS.get("google").get("api_key")
)
response = requests.get(services_url)

if response.status_code == 200: 
    services = response.json().get("services", [])
else:
    print ("Error during data fetching: ",response.status_code)
    exit()

# We have in total len(services). 1777
print ("Starting the injestion of the ",len(services)," services provided")


#Display name is the name of the service provided. For example compute engine -We will use this for the storage-
#Name and service id can be used to retrieve the json with the skus

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
        print (sku_url)
        try:
            response = requests.get(sku_url)

            if response.status_code == 200:
                data = response.json()
            else:
                print ("Error during data fetch at ",service_displayName, "with status code ", response.status_code)
                exit()


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

        except S3Error as e:
            print ("Error: ",e)
        except Exception as e:
            print ("Error: ", e)
