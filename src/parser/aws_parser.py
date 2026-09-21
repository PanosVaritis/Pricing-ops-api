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
import ijson
import json

#Αντικαθιστά το 1ο notebook. Διαβάζει τα πλήρη δεδομένα (χωρίς samples) και φτιάνχει τα dataframes
def injest_data_and_create_dfs(client, object_name) -> pd.DataFrame:

    all_products = []

    response = client.get_object(config.PROVIDERS.get("aws").get("bucket"), object_name=object_name)

    try:
        # Το ijson διαβάζει κατευθείαν από το stream byte-byte
        parser = ijson.kvitems(response, 'products')
        
        count = 0
        for sku, product_data in parser:
            #Mε την προοπτική να δημιουργεί πεδίο με sku με την αντίστοιχη τιμή μέσα στο dict αλλά αυτό ήδη υπάρχει
            # product_data['sku'] = sku
            all_products.append(product_data)

    finally:
        response.close()
        response.release_conn()

    # Μετατροπή σε αρχικό DataFrame
    df_products = pd.json_normalize(all_products)
  

    #2ο βήμα
    # Στο πάνω κελί είχα μία λίστα η οποία είχε μέσα n sku, μαζί με όλα τα attributes τουσ.
    # Τώρα στο βήμα αυτό κάνω access την λίστα και απομονώνω σε ένα set μόνο τον κωδικό των n sku (η επιλογή set βασίζεται στην γρήγορη αναζήτηση)
    target_skus = {p['sku'] for p in all_products}

    # Αυτή θα είναι η αντίστοιχη sample products του πάνω βήματος. Θα κρατάει τα ζευγάρια sku, με στοιχεία πληρωμής, και μετά θα την κάνουμε dataframe
    terms_list = []

    parser = client.get_object(config.PROVIDERS.get("aws").get("bucket"), object_name=object_name)

    try:
        # Πάμε βαθύτερα και από το λεξικό terms θα στοχεύσουμε μόνο στις On-Demand υπηρεσίες.
        terms_parser = ijson.kvitems(parser, 'terms.OnDemand')

        # Προφανώς δεν τα θέλω όλα!!Μόνο εκείνα των οποίων το sku βρίσκεται στο set το οποίο δημιούργησα
        for sku, term_offers in terms_parser:
            if sku not in target_skus:
                continue
            
            # Αποθηκεύουμε το sku και ολόκληρο το raw λεξικό των terms του
            terms_list.append({
                'skuNew': sku,
                'termsOndemand': term_offers
            })
            

    finally:
        parser.close()
        parser.release_conn()


    df_terms = pd.DataFrame(terms_list)


    #3ο βήμα
    flattened_list = []

    for idx, row in df_terms.iterrows():
        skuDefaultValue = row['skuNew']
        raw_dict = row['termsOndemand']
        
        # ΜΠετάω το αρχικό κλειδί το οποίο είχε το dict. Περισσοτερα στην αναφορά
        for hash_key, offer_content in raw_dict.items():
            
            # Εξάγω τα πεδία ένα - ένα και φτιάχνω μία δική μου δομή πιο υύκολη στην ανάλυση
            item = {
                'skuNew': skuDefaultValue,
                'offerTermCode': offer_content.get('offerTermCode'),
                'sku': offer_content.get('sku'),
                'effectiveDate': offer_content.get('effectiveDate'),
                'termAttributes': offer_content.get('termAttributes'),
                'priceDimensions': offer_content.get('priceDimensions') # Το αφήνουμε λεξικό!
            }
            flattened_list.append(item)

    df_terms = pd.DataFrame(flattened_list)

  


    #4ο βήμα
    itemsList = []

    for idx, row in df_terms.iterrows():

        # Κατασκευάζουμε εξ'ολοκλήρου νεό dataframe. Δεν κάνουμε ενέργειες πάνω στον υπάρχον. Οπότε φτιάχνουμε γραμμή γραμμή με τα πεδία που έχουμε. Για αυτό και τα εξάξουμε ένα - ένα
        skuNew = row['skuNew']
        offerTermCode = row['offerTermCode']
        skuDefaultValue = row['sku']
        effectiveDate = row['effectiveDate']
        termAttributes = row['termAttributes']
        
        # Παίρνουμε το λεξικό του priceDimensions
        priceDimensionDict = row['priceDimensions']

        # Κοιτάζει εάν όντως το priceDimensions είναι λεξικό. Αν δεν είναι δεν μπαίνει καν μέσα στο loop. Έτσι και δεν κρασάρει, και αποφεύγω να δημιουργήσω γραμμές στις οποίες τα δεδομένα είναι ελλιπή
        if isinstance(priceDimensionDict, dict):
            # ΔΌπως και στο πάνω κελί, με τον τρόπο αυτό αγνοούμε το εσωτετικό xxx.xxx.xxx
            for dimensionsDict_hash_key, dimensionsDict_content in priceDimensionDict.items():
                
                # Το pricePerUnit είναι και αυτό με την σειρά του λεξικού οποτε πριν εφαρμόσω την μέθοδο get προσέχω για να βεβαιωθώ ότι το βρήκα και δεν έπεσα στην περίπτωση "κακών" δεδομένων
                price_per_unit_dict = dimensionsDict_content.get('pricePerUnit', {})
                usd_price = price_per_unit_dict.get('USD') if isinstance(price_per_unit_dict, dict) else None
                
                item = {
                    'skuNew': skuNew,
                    'offerTermCode': offerTermCode,
                    'sku': skuDefaultValue,
                    'effectiveDate': effectiveDate,
                    'termAttributes': termAttributes,
                    'rateCode': dimensionsDict_content.get('rateCode'),
                    'description': dimensionsDict_content.get('description'),
                    'beginRange': dimensionsDict_content.get('beginRange'),
                    'endRange': dimensionsDict_content.get('endRange'),
                    'unit': dimensionsDict_content.get('unit'),
                    'priceUSD': usd_price,   # Aυτό το πεδίο μέσω του ελέγχου που κάναμε πιο πάνω, ή θα είναι None ή θα έχει κάποια τιμή. Οπότε θα το χρησιμοποιήσω μετά για έλεγχω
                    'appliesTo': dimensionsDict_content.get('appliesTo')
                }
                itemsList.append(item)

    df_terms_final = pd.DataFrame(itemsList)

    process_terms(df_terms_final=df_terms_final)

    return df_terms_final, df_products

   

#5ο βήμα: Επεξεργασία του πίνακα τιμών
def process_terms(df_terms_final) -> pd.DataFrame:

    df_terms_final = df_terms_final.explode('appliesTo').reset_index(drop=True)

    if 'termAttributes' in df_terms_final.columns:
        df_terms_final = df_terms_final.drop(columns=['termAttributes'])


    #Βάζω το if για να μπορώ να τρέχω το κελί και μόνο του χωρίς να πετάει error (έχω 2 στήλες με sku. κρατά την μία μόνο μετά από έναν έλεγχο)
    if 'skuNew' in df_terms_final.columns and 'sku' in df_terms_final.columns:

        # Φτιάχνω την συνθήκη ελέγχου - διαγραφής μιας υπηρεσίας και την εφαρμόζω απευθείας μετά πάνω στο dataframe. Γλιτώνω το loop 
        condition = (df_terms_final['skuNew'] == df_terms_final['sku'])

        df_filtered_terms = df_terms_final[condition]

        df_terms_final = df_filtered_terms.copy()


    if 'skuNew' in df_terms_final.columns:
        df_terms_final = df_terms_final.drop(columns=['skuNew'])

 

    if 'effectiveDate' in df_terms_final.columns:
        df_terms_final = df_terms_final.drop(columns=['effectiveDate'])



    if 'beginRange' in df_terms_final.columns and 'endRange' in df_terms_final.columns:

        df_terms_final = df_terms_final[df_terms_final['beginRange'] == '0']

        df_terms_final.drop(columns=['beginRange', 'endRange'], inplace=True)

    df_terms_final.reset_index(drop=True, inplace=True)



    df_terms_final['priceUSD'] = pd.to_numeric(df_terms_final['priceUSD'], errors='coerce')

    df_terms_final = df_terms_final[df_terms_final['priceUSD'] > 0]

    df_terms_final.reset_index(drop=True, inplace=True)

  

    if 'appliesTo' in df_terms_final.columns:
        df_terms_final = df_terms_final[df_terms_final['appliesTo'].isna()]

        df_terms_final.reset_index(drop=True, inplace=True)

        df_terms_final.drop(columns=['appliesTo'], errors='ignore', inplace=True)

  
    colsToCheck = ['sku', 'priceUSD', 'unit']
    df_terms_final.dropna(subset=colsToCheck, inplace=True)
    df_terms_final.reset_index(drop=True, inplace=True)


    if 'offerTermCode' in df_terms_final.columns:
        df_terms_final.drop(columns=['offerTermCode'], errors='ignore', inplace=True)

    return df_terms_final

 


#Το pipeline για EC2 (Instances, Bare Metal, Storage & Extras)
def parse_ec2_compute(df_products, df_terms, client):

    if 'attributes.marketoption' in df_products.columns:
        df_products.drop(columns=['attributes.marketoption'], errors='ignore', inplace=True)

    if 'attributes.servicename' in df_products.columns:
        df_products.drop(columns=['attributes.servicename'], errors='ignore', inplace=True)


    #Προκύτπουν από το ec2 3 επίμέρους αρχεία με καθαρά δεδομένα
    df_compute = df_products[df_products['productFamily'] == 'Compute Instance'].reset_index(drop=True)

    df_bare_metal = df_products[df_products['productFamily'] == 'Compute Instance (bare metal)'].reset_index(drop=True)

    df_extras = df_products[~df_products['productFamily'].isin(['Compute Instance', 'Compute Instance (bare metal)'])].reset_index(drop=True)


    #1ο dataframe, αφορά compute instance
    id_columns = ['sku', 'productFamily', 'attributes.servicecode', 'attributes.location', 'attributes.locationType']

    #Πεδία χαρακτηρισμού
    feature_columns = ['attributes.instanceType', 'attributes.instanceFamily', 'attributes.instanceFamilyCategory', 'attributes.vcpu', 'attributes.memory', 'attributes.operatingSystem',
                   'attributes.tenancy', 'attributes.processorArchitecture', 'attributes.physicalProcessor', 'attributes.clockSpeed', 'attributes.storage']


    total = []
    total.extend(id_columns)
    total.extend(feature_columns)
    df_compute[total].head()


    # Βρίσκουμε ποιες στήλες του DataFrame ΔΕΝ περιέχονται στη λίστα 'total'. Η total περιέχει όλα τα στοιχεία που θέλω να κρατήσω ως βασικά
    remaining_cols = [col for col in df_compute.columns if col not in total]

    #Δημιουργώ αντίγραφο του compute με τις στήλες που θέλω
    df_final_compute = df_compute[total].copy()

    #Φτιάχνω μία νέα στήλη με τις υπολοιπόμενες στήλες σε μορφή λεξικού
    df_final_compute['additionalAttributes'] = df_compute[remaining_cols].apply(
        lambda row: json.dumps({k: v for k, v in row.to_dict().items() if pd.notna(v)}), 
        axis=1
    )

    #κάνω merge τον πίνακα compute με τον πίνακα των τιμών βάση του sku. Επειδή έιχα 2 στήλες sku με το ίδιο όνομα η μία φεύγει. Για να μπει ένα πεδίο
    #, στον τελικό πίνακακ πρέπει να υπάρχει και στους 2 το sku. Ουσιαστικά παίρνει γραμμή 1 τουc compute, ψάνψει όλο το terms για το sku αυτό, και αν το
    # βρει φτιάνει νέα εγγραφή στον πίνακα master, αλλιώς το αφήνει εκτός. Και συνεχίζει. Δεν ανησυχώ για διπλότυπα. Βάση του καθαρισμού δεν υπάρχουν, αλλά και να υπάρχουν τα διαχειρίζεται η εντολή
    
    df_master_compute = pd.merge(df_final_compute, df_terms, on='sku', how='inner').reset_index(drop=True)


    #2o dataframe αφορά compute bare metal
    id_columns_metal = ['sku','productFamily', 'attributes.servicecode', 'attributes.location', 'attributes.locationType']

    feature_columns_metal = [ 'attributes.instanceType', 'attributes.instanceFamily', 'attributes.instanceFamilyCategory', 'attributes.vcpu', 'attributes.memory', 'attributes.operatingSystem',
                            'attributes.tenancy', 'attributes.processorArchitecture', 'attributes.physicalProcessor', 'attributes.clockSpeed','attributes.storage',
                            'attributes.networkPerformance','attributes.dedicatedEbsThroughput']

    total_metal = []
    total_metal.extend(id_columns_metal)
    total_metal.extend(feature_columns_metal)


    remaining_cols_metal = [col for col in df_bare_metal.columns if col not in total_metal]
    df_final_metal = df_bare_metal[total_metal].copy()

    df_final_metal['additionalAttributes'] = df_bare_metal[remaining_cols_metal].apply(
        lambda row: json.dumps({k: v for k, v in row.to_dict().items() if pd.notna(v)}), 
        axis=1
    )


    df_master_metal = pd.merge(df_final_metal, df_terms, on='sku', how='inner').reset_index(drop=True)


    #3o dataframe αφορά όλα τα άλλα
    id_columns_extras = ['sku', 'productFamily', 'attributes.servicecode', 'attributes.location', 'attributes.locationType']   


    remaining_cols_extras = [col for col in df_extras.columns if col not in id_columns_extras]

    df_final_extras = df_extras[id_columns_extras].copy()

    # Επιπλέον στήλη με όλες τις όχι βασικές στήλες. Πετάμε NAN 
    df_final_extras['additional_attributes'] = df_extras[remaining_cols_extras].apply(
        lambda row: json.dumps({k: v for k, v in row.to_dict().items() if pd.notna(v)}), 
        axis=1
    )

    df_master_extras = pd.merge( df_final_extras, df_terms, on='sku', how='inner').reset_index(drop=True)


    datasets_to_upload = {
        "aws_ec2_compute_clean.csv": df_master_compute,
        "aws_ec2_compute_metal_clean.csv": df_master_metal,
        "aws_ec2_extras_clean.csc": df_master_extras
    }

    for file_name, df in datasets_to_upload.items():
        csv_bytes = df.to_csv(index=False).encode('utf-8')
        
        client.put_object(
            bucket_name=config.PROVIDERS.get("aws").get("clean_bucket"),
            object_name=file_name,
            data=io.BytesIO(csv_bytes),
            length=len(csv_bytes),
            content_type='application/csv'
        )





#Το pipeline για S3 (Storage Master & Operations Master)
def parse_s3(df_products, df_terms, client):

    if 'attributes.servicename' in df_products.columns:
        df_products.drop(columns=['attributes.servicename'], errors='ignore', inplace=True)


    # Aπό το s3 θα προκύψουν 2 επιμέρους dataframes
    df_s3_storage = df_products[df_products['productFamily'] == 'Storage'].reset_index(drop=True)

    df_s3_operations = df_products[df_products['productFamily'] != 'Storage'].reset_index(drop=True)

    #1o Dataframe 
    id_columns_s3_stor = ['sku', 'productFamily', 'attributes.servicecode', 'attributes.location', 'attributes.locationType']

    feature_columns_s3_stor = ['attributes.usagetype', 'attributes.storageClass', 'attributes.volumeType', 'attributes.availability', 'attributes.durability']

    total_s3_stor_cols = id_columns_s3_stor + feature_columns_s3_stor

    remaining_cols_s3_stor = [col for col in df_s3_storage.columns if col not in total_s3_stor_cols]

    df_final_s3_storage = df_s3_storage[total_s3_stor_cols].copy()
    df_final_s3_storage['additional_attributes'] = df_s3_storage[remaining_cols_s3_stor].apply(
        lambda row: json.dumps({k: v for k, v in row.to_dict().items() if pd.notna(v)}), 
        axis=1
    )

    df_master_s3_storage = pd.merge(df_final_s3_storage, df_terms, on='sku', how='inner').reset_index(drop=True)


    #2o Dataframe
    id_columns_s3_ops = ['sku', 'productFamily', 'attributes.servicecode', 'attributes.location', 'attributes.locationType', 'attributes.regionCode']

    feature_columns_s3_ops = ['attributes.usagetype', 'attributes.operation', 'attributes.transferType','attributes.fromLocation', 'attributes.fromLocationType', 'attributes.toLocation',
                            'attributes.toLocationType', 'attributes.fromRegionCode', 'attributes.toRegionCode', 'attributes.feeCode', 'attributes.feeDescription', 'attributes.group',
                            'attributes.groupDescription', 'attributes.storageClass','attributes.volumeType']


    total_s3_ops_cols = id_columns_s3_ops + feature_columns_s3_ops

    remaining_cols_s3_ops = [col for col in df_s3_operations.columns if col not in total_s3_ops_cols]

    df_final_s3_operations = df_s3_operations[total_s3_ops_cols].copy()
    df_final_s3_operations['additional_attributes'] = df_s3_operations[remaining_cols_s3_ops].apply(
        lambda row: json.dumps({k: v for k, v in row.to_dict().items() if pd.notna(v)}), 
        axis=1
    )

    df_master_s3_operations = pd.merge(df_final_s3_operations, df_terms, on='sku', how='inner').reset_index(drop=True)



    datasets_to_upload = {
        "aws_s3_storage_clean.csv": df_master_s3_storage,
        "aws_s3_operations_clean.csv": df_master_s3_operations
    }

    for file_name, df in datasets_to_upload.items():
        csv_bytes = df.to_csv(index=False).encode('utf-8')
        
        client.put_object(
            bucket_name=config.PROVIDERS.get("aws").get("clean_bucket"),
            object_name=file_name,
            data=io.BytesIO(csv_bytes),
            length=len(csv_bytes),
            content_type='application/csv'
        )



#  Το pipeline για RDS (Instances, Storage, Extras)
def parse_rds(df_products, df_terms, client):

    if 'attributes.servicename' in df_products.columns:
        df_products.drop(columns=['attributes.servicename'], errors='ignore', inplace=True)


    #Aπό το rds θα προκύψουν 3 επιμέτους Dataframe
    df_database_instance= df_products[df_products['productFamily'] == 'Database Instance'].reset_index(drop=True)

    target_storage_families = ['Database Storage', 'Provisioned IOPS']
    df_rds_storage = df_products[df_products['productFamily'].isin(target_storage_families)].reset_index(drop=True)

    excluded_families = ['Database Instance', 'Database Storage', 'Provisioned IOPS']
    df_rds_extras = df_products[~df_products['productFamily'].isin(excluded_families)].reset_index(drop=True)


    #1o dataframe (Database instance)
    id_columns_db_instance = ['sku', 'productFamily', 'attributes.servicecode', 'attributes.location', 'attributes.locationType']

    feature_columns_db_instance = ['attributes.instanceType', 'attributes.instanceFamily', 'attributes.vcpu', 'attributes.memory', 'attributes.storage', 'attributes.physicalProcessor', 
                                'attributes.networkPerformance', 'attributes.databaseEngine','attributes.databaseEdition', 'attributes.licenseModel', 'attributes.deploymentOption']

    total_db_instance = []
    total_db_instance.extend(id_columns_db_instance)
    total_db_instance.extend(feature_columns_db_instance)
    df_database_instance[total_db_instance].head()


    remaining_cols_rds = [col for col in df_database_instance.columns if col not in total_db_instance]

    df_final_database_instance = df_database_instance[total_db_instance].copy()

    df_final_database_instance['additional_attributes'] = df_database_instance[remaining_cols_rds].apply(
        lambda row: json.dumps({k: v for k, v in row.to_dict().items() if pd.notna(v)}), 
        axis=1
    )

    df_master_database_instance = pd.merge(df_final_database_instance, df_terms, on='sku', how='inner').reset_index(drop=True)



    #2o dataframe (Storage and iops)
    id_columns_storage = ['sku', 'productFamily', 'attributes.servicecode', 'attributes.location', 'attributes.locationType']

    feature_columns_storage = ['attributes.volumeName', 'attributes.volumeType', 'attributes.storageMedia', 'attributes.minVolumeSize', 'attributes.maxVolumeSize', 
                               'attributes.databaseEngine', 'attributes.deploymentOption', 'attributes.usagetype']

    total_storage_cols = id_columns_storage + feature_columns_storage

    remaining_cols_storage = [col for col in df_rds_storage.columns if col not in total_storage_cols]

    df_final_storage = df_rds_storage[total_storage_cols].copy()

    df_final_storage['additional_attributes'] = df_rds_storage[remaining_cols_storage].apply(
        lambda row: json.dumps({k: v for k, v in row.to_dict().items() if pd.notna(v)}), 
        axis=1
    )

    df_master_storage = pd.merge(df_final_storage, df_terms, on='sku', how='inner').reset_index(drop=True)



    #3o dataframe (rest)
    id_columns_extras = ['sku', 'productFamily', 'attributes.servicecode', 'attributes.location', 'attributes.locationType']

    feature_columns_extras = ['attributes.usagetype','attributes.operation', 'attributes.databaseEngine','attributes.engineMajorVersion',
                            'attributes.extendedSupportPricingYear','attributes.group', 'attributes.acu']


    total_extras_cols = id_columns_extras + feature_columns_extras

    remaining_cols_extras = [col for col in df_rds_extras.columns if col not in total_extras_cols]

    df_final_extras = df_rds_extras[total_extras_cols].copy()
    df_final_extras['additional_attributes'] = df_rds_extras[remaining_cols_extras].apply(
        lambda row: json.dumps({k: v for k, v in row.to_dict().items() if pd.notna(v)}), 
        axis=1
    )

    df_master_extras = pd.merge(df_final_extras, df_terms, on='sku', how='inner').reset_index(drop=True)


    datasets_to_upload = {
        "aws_rds_instances_clean.csv": df_master_database_instance,
        "aws_rds_storage_clean.csv": df_master_storage,
        "aws_rds_extras_clean.csv": df_master_extras
    }

    for file_name, df in datasets_to_upload.items():
        csv_bytes = df.to_csv(index=False).encode('utf-8')
        
        client.put_object(
            bucket_name=config.PROVIDERS.get("aws").get("clean_bucket"),
            object_name=file_name,
            data=io.BytesIO(csv_bytes),
            length=len(csv_bytes),
            content_type='application/csv'
        )



#Το pipeline για VPC (Ενιαίο Master)
def parse_vpc(df_products, df_terms, client):

    if 'attributes.servicename' in df_products.columns:
        df_products.drop(columns=['attributes.servicename'], errors='ignore', inplace=True)

    id_columns_vpc = ['sku', 'productFamily', 'attributes.servicecode', 
                'attributes.location', 'attributes.locationType', 'attributes.regionCode']

    feature_columns_vpc = ['attributes.usagetype','attributes.operation','attributes.endpointType','attributes.vpnType', 'attributes.attachmentType',
                    'attributes.trafficDirection', 'attributes.transferType', 'attributes.fromLocation', 'attributes.fromLocationType',
                    'attributes.toLocation', 'attributes.toLocationType', 'attributes.fromRegionCode', 'attributes.toRegionCode',
                    'attributes.group', 'attributes.groupDescription']


    total_vpc_cols = id_columns_vpc + feature_columns_vpc

    remaining_cols_vpc = [col for col in df_products.columns if col not in total_vpc_cols]

    df_final_vpc = df_products[total_vpc_cols].copy()
    if remaining_cols_vpc:
        df_final_vpc['additional_attributes'] = df_products[remaining_cols_vpc].apply(
            lambda row: json.dumps({k: v for k, v in row.to_dict().items() if pd.notna(v)}), 
            axis=1
        )
    else:
        df_final_vpc['additional_attributes'] = "{}"

    df_master_vpc = pd.merge(df_final_vpc, df_terms, on='sku', how='inner').reset_index(drop=True)

    csv_bytes = df_master_vpc.to_csv(index=False).encode('utf-8')
    clean_object_name = "aws_vpc_clean.csv"

    client.put_object (
        bucket_name=config.PROVIDERS.get("aws").get("clean_bucket"),
        object_name=clean_object_name,
        data=io.BytesIO(csv_bytes),
        length=len(csv_bytes),
        content_type='application/csv'
        )



#Το pipeline για EKS (Ενιαίο Master με απευθείας JOIN)
def parse_eks(df_products, df_terms, client):

    if 'attributes.servicename' in df_products.columns:
        df_products.drop(columns=['attributes.servicename'], errors='ignore', inplace=True)

    df_products.drop(columns=['attributes.regionCode'], errors='ignore', inplace=True)

    df_master_eks = pd.merge(df_products, df_terms, on='sku', how='inner').reset_index(drop=True)

    csv_bytes = df_master_eks.to_csv(index=False).encode('utf-8')
    clean_object_name = "aws_eks_clean.csv"

    client.put_object (
        bucket_name=config.PROVIDERS.get("aws").get("clean_bucket"),
        object_name=clean_object_name,
        data=io.BytesIO(csv_bytes),
        length=len(csv_bytes),
        content_type='application/csv'
        )

    

# Ρυθμίζει όλη την εκτέλεση
def run_aws_pipeline(client):

    # services = ['AmazonEC2.json', 'AmazonS3.json']
    services= ['AmazonEKS.json', 'AmazonVPC.json', 'AmazonRDS.json', 'AmazonS3.json']
    for object_name in services:

        df_terms, df_products = injest_data_and_create_dfs(client=client, object_name=object_name)
        logging.info(f"Sucessfuly created {object_name} service dataframes")

        if object_name == 'AmazonEKS.json':
            parse_eks(df_terms=df_terms, df_products=df_products, client=client)
            logging.info("Sucessfully parsed eks")
        elif object_name == 'AmazonVPC.json':
            parse_vpc(df_products=df_products, df_terms=df_terms, client=client)
            logging.info("Sucessfully parsed vpc")
        elif object_name == 'AmazonRDS.json':
            parse_rds(df_products=df_products, df_terms=df_terms, client=client)
            logging.info("Sucessfully parsed EDS")
        elif object_name == 'AmazonS3.json':
            parse_s3(df_products=df_products, df_terms=df_terms, client=client)
            logging.info("Sucessfully parsed S3")

    
    
def main():

    
    utils.set_up_logger()
    logging.info ("Starting azure pipeline execution")

    client = config.create_minio_client()
    logging.info ("Succesfully created client")

    if not utils.bucket_creation(client, config.PROVIDERS.get("aws").get("clean_bucket")):
        return


    run_aws_pipeline(client=client)



if __name__ == "__main__":
    main()