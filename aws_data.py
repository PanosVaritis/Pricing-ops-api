import requests
import config
from minio.error import S3Error

client = config.create_minio_client()

try:
    if not client.bucket_exists(config.PROVIDERS["aws"]["bucket"]):
        print("Bucket does not exist -> Creating new")
        client.make_bucket(config.PROVIDERS["aws"]["bucket"])

except S3Error as e:
    print("Error:", e)
    exit()

response = requests.get(config.PROVIDERS.get("aws").get("base_url") + config.PROVIDERS.get("aws").get("index_extension"))


if response.status_code == 200:
    data = response.json()
else:
    print ("Error during data fetch:", response.status_code)
    exit()


for key, value in data.get("offers").items():
#Here the key is the service name and the value is the dict that has the info

    current_url_extension = value.get("currentVersionUrl")

    #If value is None -the default from .get in dict this if will be skipped
    if current_url_extension:

        full_url = config.PROVIDERS.get("aws").get("base_url") + current_url_extension
        
        print(f"Streaming {key} from: {full_url}")
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
            print ("Error",key,e)

        except Exception as e:
            print ("Error:",key,e)
