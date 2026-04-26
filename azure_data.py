import requests
from minio.error import S3Error
import json
import config
import io

client = config.create_minio_client()

try:
    if not client.bucket_exists(config.PROVIDERS["azure"]["bucket"]):
        print("Bucket does not exist -> Creating new")
        client.make_bucket(config.PROVIDERS["azure"]["bucket"])

except S3Error as e:
    print("Error:", e)
    exit()


file_counter = 0
azure_url = config.PROVIDERS.get("azure").get("url")

while azure_url:
    print ("Fetching data from: ",azure_url)

    response = requests.get(azure_url)

    if response.status_code == 200:
        data = response.json()
    else:
        print ("Error during data fetching:", response.status_code)


    json_data = json.dumps(data).encode('utf-8')
    data_stream = io.BytesIO(json_data)

    client.put_object(
            config.PROVIDERS.get("azure").get("bucket"),
            f"azure_{file_counter}.json",
            data_stream,
            length=len(json_data),
            content_type='application/json'
        )
    
    azure_url = data.get("NextPageLink")
    file_counter += 1000

















#     azure_url = data.get("NextPageLink")
#     print (azure_url)

#     #Take query params from azure_url
#     parsed = urlparse(azure_url)
#     params = parse_qs(parsed.query)
#     file_counter = params.get("$skip")[0]


