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

#Creating a stable schema of 29 columns for google. This is as high as it can get
GOOGLE_FORMAT = [
    'name', 'skuId', 'description', 'serviceRegions', 'serviceProviderName',
    'category.serviceDisplayName', 'category.resourceFamily', 'category.resourceGroup',
    'category.usageType', 'geoTaxonomy.type', 'geoTaxonomy.regions', 'summary',
    'currencyConversionRate', 'effectiveTime', 'pricingExpression.usageUnit',
    'pricingExpression.displayQuantity', 'pricingExpression.usageUnitDescription',
    'pricingExpression.baseUnit', 'pricingExpression.baseUnitDescription',
    'pricingExpression.baseUnitConversionFactor', 'aggregationInfo.aggregationLevel',
    'aggregationInfo.aggregationInterval', 'aggregationInfo.aggregationCount',
    'startUsageAmount', 'unitPrice.currencyCode', 'unitPrice.units', 'unitPrice.nanos',
    'finalPrice', 'final_price_usd'
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

    final_df = df_clean_no_nan.reindex(columns=GOOGLE_FORMAT)
    
    return final_df
