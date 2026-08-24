import pandas as pd
import numpy as np
import sys, os
current = os.path.dirname(__file__)
path_to_root = os.path.join (current, '../..')
abs_path = os.path.abspath(path_to_root)
sys.path.append(abs_path)
import config
import io
from minio.error import S3Error
import utils
import logging


#This is filtering based on serviceName and not based on serviceFamily
SERVICE_LIST = [ 
    "Virtual Machines", "Virtual Machines Licenses", 
    "Azure Kubernetes Service", "Container Instances", "Azure Container Apps",
    "Azure Database for PostgreSQL", "Azure Database for MySQL", "SQL Database", "Azure Database for MariaDB", "Azure Cosmos DB",
    "Storage", "Backup",
    "Bandwidth", "Virtual Network", "Load Balancer"
    ]


def azure_parse (response) -> pd.DataFrame:
    
    df = pd.read_json(response)

    if 'Items' in df.columns:
        df_flat = pd.json_normalize(df['Items'])

    if df_flat.empty:
        return pd.DataFrame()

    # Η παρακάτω μεταβλητή κρατάει το πλήθος των κενών τιμών από την στήλη με τον τύπο νομίσματος. Η μεταβλητή δεν είναι νεο df, απλή μεταβλητή int
    nan_count = df_flat['currencyCode'].isna().sum()

    # Αν βρούμε έστω και μία Nan τιμή τρέχουμε μπαίνει στο loop για να την πετάξει και επαναφέρει και το index στις άλλες εγγραφές
    if nan_count > 0:
        df_flat = df_flat.dropna(subset=['currencyCode']).reset_index(drop=True)


    #Κρατάμε μόνο θετικές τιμές στο retailPrice (Nan και 0 τα πετάει)
    zero_nan= (df_flat['retailPrice'] <= 0) | (df_flat['retailPrice'].isna())
    zero_nan_count = zero_nan.sum()


    if zero_nan_count > 0:
        df_flat= df_flat[df_flat['retailPrice'] > 0].reset_index(drop=True)

    #Πετάμε την στήλη unitPrice, καθώς δεν μας χρειάζεται
    if 'unitPrice' in df_flat.columns:
        df_flat.drop(columns=['unitPrice'], inplace=True)

    #Κρατάμε μόνο τις εγγραφές τύπου consumption, πετώντας τις υπόλοιπες, καθώς και την τελευταία στήλη που αφορούσε διάρκειες συμβολαίων
    df_flat = df_flat[df_flat['type'] == 'Consumption']
    df_flat = df_flat.reset_index(drop=True)

    if 'reservationTerm' in df_flat.columns:
        df_flat.drop(columns=['reservationTerm'], inplace=True)

    #Πετάω την στήλη effectibeStartDate αφού φτιάχνουμε το έργο χωρίς ιστορικότητα
    if 'effectiveStartDate' in df_flat.columns:
        df_flat.drop(columns=['effectiveStartDate'], inplace=True)

    #Πετάω και το endDate για ομοιομορφία αλλά και επειδή δεν χρειάζεται
    if 'effectiveEndDate' in df_flat.columns:
        df_flat.drop(columns=['effectiveEndDate'], inplace=True)

    return df_flat


def run_azure_pipeline(client):

    services_set = {service: [] for service in SERVICE_LIST}

    objects = client.list_objects(config.PROVIDERS.get("azure").get("bucket"))

    for obj in objects:
        logging.info (f"Processing {obj.object_name}")

        response = client.get_object(config.PROVIDERS.get("azure").get("bucket"), obj.object_name)

        try :
            df_page = azure_parse(response=response)

            if not df_page.empty :

                for service in SERVICE_LIST:
                    df_service_page = df_page[df_page['serviceName'] == service]


                    if not df_service_page.empty: 
                        services_set[service].append(df_service_page)

        except Exception as e:
            logging.error(f"Error while processing {obj.object_name}. Error message: {e}")

        finally:
            response.close()
            response.release_conn()


    for service, dataframe_list in services_set.items():
        if dataframe_list:

            final_df = pd.concat(dataframe_list, ignore_index=True)

            csv_buffer = io.StringIO()
            final_df.to_csv(csv_buffer, index=False)
            csv_bytes = csv_buffer.getvalue().encode('utf-8')

            clean_object_name = f"{service.lower().replace(' ', '_')}_clean.csv"

            client.put_object(
                config.PROVIDERS.get("azure").get("clean_bucket"),
                clean_object_name,
                data=io.BytesIO(csv_bytes),
                length=len(csv_bytes),
                content_type='application/csv'
            )

            logging.info(f"Stored {clean_object_name} with {len(final_df)} rows and {final_df.shape[1]} columns in Minio clean bucket.")
        else:
            logging.warning(f"Not valid dataframes founds. Unexpected error occured {service}")

    logging.info("Azure Pipeline completed successfully")
    

def main():
    
    utils.set_up_logger()
    logging.info ("Starting azure pipeline execution")

    client = config.create_minio_client()
    logging.info ("Succesfully created client")

    if not utils.bucket_creation(client, config.PROVIDERS.get("azure").get("clean_bucket")):
        return


    run_azure_pipeline(client=client)

if __name__ == "__main__":
    main()
