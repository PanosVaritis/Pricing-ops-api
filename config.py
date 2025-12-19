from minio import Minio


client = Minio(
    "172.18.0.2:9000", 
    access_key="panos", 
    secret_key="panosvaritis2003", 
    secure=False,  
)

bucket = "azure"

path = "/home/panos-varitis/rerl/uni/ptyxiaki/apiexamples/stored_files"

azure_url = "https://prices.azure.com/api/retail/prices"


