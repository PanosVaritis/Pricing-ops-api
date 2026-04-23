import requests
import config
import json
from minio.error import S3Error

client = config.create_minio_client()

try:
    if not client.bucket_exists(config.PROVIDERS["aws"]["bucket"]):
        print("Bucket does not exist -> Creating new")
        client.make_bucket(config.PROVIDERS["aws"]["bucket"])

except S3Error as e:
    print("Error:", e)
    exit()

response = requests.get(config.PROVIDERS["aws"]["base_url"] + config.PROVIDERS["aws"]["index_extension"])


if response.status_code == 200:
    data = response.json()
else:
    print ("Error during data fetch:", response.status_code)
    exit()


base_file_name = config.PROVIDERS["aws"]["path"] + "/index.json"

try:
    with open(base_file_name, 'w') as fi:
        json.dump(data, fi)

#The first file name is the name that the file will have in minio and the second in the name locally
        client.fput_object(config.PROVIDERS["aws"]["bucket"], 'index.json', base_file_name)  

except S3Error as e:
    print("Error:",e)

except Exception as e:
    print("Error:",e)   


base_file_name = config.PROVIDERS["aws"]["path"] +"/"

for key, value in data.get("offers").items():
    # print (key) #this is the service name

    # print (base_file_name+key+".json")

    for key1, value1 in value.items():

        if key1 == "currentVersionUrl":

            print (config.PROVIDERS["aws"]["base_url"] + value1)
    

            response = requests.get(config.PROVIDERS["aws"]["base_url"] + value1)

            if response.status_code == 200:
                data = response.json()
            else:
                print ("Error while trying to fetch data")
            
            file_name = base_file_name + key + ".json"

            try :  
                with open (file_name, 'w') as fi:
                    json.dump(data, fi)

                    client.fput_object(config.PROVIDERS["aws"]["bucket"], key+".json", file_name)

            except S3Error as e:
                print ("Error:",e)
    
            except Exception as e:
                print ("Error:", e)

