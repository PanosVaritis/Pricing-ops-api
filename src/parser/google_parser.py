"""
Those are the services that we are intrested for
Kubernetes_Engine: 1 page, 1.4 Mib, 1731rows
Compute_Engine: 7 pages, 4.1Mib and 1.1Mib, 5000 rows/page
Cloud_Storage: 1 page, 1000Kib, 1220 services, 3000 with duplicates
Cloud_SQL : 4 pages
Networking: 1 page, 1600 services, 2800 non unique

"""

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

#Creating a stable schema of 29 columns for google. This is as high as it can get
GOOGLE_FORMAT = [
    'name', 'skuId', 'description', 'serviceRegions', 'serviceProviderName',
    'category.serviceDisplayName', 'category.resourceFamily', 'category.resourceGroup',
    'category.usageType', 'geoTaxonomy.type', 'geoTaxonomy.regions', 'summary',
    'effectiveTime', 'pricingExpression.usageUnit',
    'pricingExpression.displayQuantity', 'pricingExpression.baseUnit', 
    'pricingExpression.baseUnitConversionFactor', 'aggregationInfo.aggregationLevel',
    'aggregationInfo.aggregationInterval', 'aggregationInfo.aggregationCount',
    'startUsageAmount', 'unitPrice.currencyCode', 'finalPrice', 'final_price_usd'
]

#Creating a mold for the services that we are going to analyze
SERVICE_LIST = ["Kubernetes_Engine", "Compute_Engine", "Cloud_SQL", "Cloud_Storage", "Networking"]  

#Takes raw json stream from minion (data of google cloud billing api) and returns clean dataframe of 29 columns
def google_parse(response) -> pd.DataFrame:
    
    df = pd.read_json(response)

    df_flat = pd.json_normalize(df['skus'])
    
    if df_flat.empty:
        return pd.DataFrame(columns=GOOGLE_FORMAT)
    
    df_flat2 = df_flat.explode('geoTaxonomy.regions')
        
    df_flat3 = df_flat2.explode('serviceRegions')

    df_flat4 = df_flat3.explode('pricingInfo')

    pricing1 = pd.json_normalize(df_flat4['pricingInfo'])

    pricing1.index = df_flat4.index

    df_flat5 = pd.concat([df_flat4.drop(columns=['pricingInfo']), pricing1], axis=1)

    df_flat6 = df_flat5.explode('pricingExpression.tieredRates')

    pricing2 = pd.json_normalize(df_flat6['pricingExpression.tieredRates'])

    pricing2.index = df_flat6.index

    df_flat7 = pd.concat([df_flat6.drop(columns=['pricingExpression.tieredRates']), pricing2], axis=1)

    df_flat7['finalPrice'] = df_flat7['unitPrice.units'].astype(float) + (df_flat7['unitPrice.nanos'].astype(float) / 1000000000)

    df_clean_no_nan = df_flat7.dropna(subset=['unitPrice.currencyCode']).copy()

    rate = df_clean_no_nan['currencyConversionRate'].astype(float)

    df_clean_no_nan['final_price_usd'] = df_clean_no_nan['finalPrice'].astype(float) / rate

    df_clean_no_nan.drop(columns=['pricingExpression.usageUnitDescription', 'pricingExpression.baseUnitDescription'], errors='ignore', inplace=True)

    df_clean_no_nan.drop(columns=['currencyConversionRate', 'unitPrice.units', 'unitPrice.nanos'], errors='ignore', inplace=True)

    final_df = df_clean_no_nan.reindex(columns=GOOGLE_FORMAT)
    
    return final_df




"""
It is almost magic. This pretty little function reads all the pages inside the service folder page_*.json,
takes them thought the parser, and uploads them in a single csv or parquet in a clean bucket in minio 
"""
def run_google_pipeline(client):

    for service in SERVICE_LIST:

        objects = client.list_objects(config.PROVIDERS.get("google").get("bucket"), prefix=service, recursive=True)

        df_list = []

        for obj in objects:

            logging.info (f"Processing {obj.object_name}")
            
            response = client.get_object(config.PROVIDERS.get("google").get("bucket"), object_name=obj.object_name)

            try:
                df_page = google_parse(response=response)

                #It is possible for the parser to return a 29 column array with 0 records. We are prepaired for this
                if not df_page.empty:
                    df_list.append(df_page)
            except Exception as e:
                logging.error (f"Error in page {obj.object_name}: {e}")
            finally:
                response.close()
                response.release_conn()

        #In this part we will concatenate all the pages of the service. If they are many
        if df_list:
            df_all_pages = pd.concat(df_list, ignore_index=True)

            # Μετατροπή σε CSV Bytes στη μνήμη
            csv_buffer = io.StringIO()
            df_all_pages.to_csv(csv_buffer, index=False)
            csv_bytes = csv_buffer.getvalue().encode('utf-8')
            
            clean_object_name = f"{service}_clean.csv"

            client.put_object(
                config.PROVIDERS.get("google").get("clean_bucket"),
                clean_object_name,
                data=io.BytesIO(csv_bytes),
                length=len(csv_bytes),
                content_type='application/csv'
            )
            logging.info (f"Stored {clean_object_name} with {len(df_all_pages)} rows ansd {df_all_pages.shape[1]} cols in Minio clean bucket.")
        else:
            logging.warning ("Not valid dataframes founds. Unexpected error occured")

    logging.info ("Google Pipeline completed successfully")



def main():
    
    utils.set_up_logger()
    logging.info ("Starting google pipeline execution")

    client = config.create_minio_client()
    logging.info ("Succesfully created client")

    if not utils.bucket_creation(client, config.PROVIDERS.get("google").get("clean_bucket")):
        return


    run_google_pipeline(client=client)

if __name__ == "__main__":
    main()