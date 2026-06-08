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

def bucket_creation(client):

    try:
        if not client.bucket_exists(config.PROVIDERS.get("azure").get("bucket")):
            print("Bucket does not exist -> Creating new")
            client.make_bucket(config.PROVIDERS.get("azure").get("bucket"))

    except S3Error as e:
        print("Error:", e)
        return False
    
    return True



def service_injestion (client):

    file_counter = 1
    azure_url = config.PROVIDERS.get("azure").get("url")

    while azure_url:
        print ("Fetching page ", file_counter, " from: ",azure_url)

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
                print ("Error during data fetching:", response.status_code)
                break

        except Exception as e:
            print ("Connection error: ",e)



def main():

    print ("Starting azure data injestion")

    try:

        client = config.create_minio_client()
        print ("Succesfully created client")

        if bucket_creation(client):
        
            print ("Bucket creation completed")
            print ("Starting injestion")
            service_injestion(client=client)

        print ("Azure data injestion finished")

    except Exception as e:
        print ("Unknown error", e)



if __name__ == "__main__":
    main()



#     azure_url = data.get("NextPageLink")
#     print (azure_url)

#     #Take query params from azure_url
#     parsed = urlparse(azure_url)
#     params = parse_qs(parsed.query)
#     file_counter = params.get("$skip")[0]


