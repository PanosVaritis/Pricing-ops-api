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


#Αντικαθιστά το 1ο notebook. Διαβάζει τα πλήρη δεδομένα (χωρίς samples), καθαρίζει τα On-Demand terms και τα αποθηκεύει
def process_terms_and_base(client) -> pd.DataFrame:

    object_name = ""


    TARGET_RECORDS = 100000 
    sample_products = []

    response = client.get_object(config.PROVIDERS.get("aws").get("bucket"), object_name=object_name)

    try:
        # Το ijson διαβάζει κατευθείαν από το stream byte-byte
        parser = ijson.kvitems(response, 'products')
        
        count = 0
        for sku, product_data in parser:
            #Mε την προοπτική να δημιουργεί πεδίο με sku με την αντίστοιχη τιμή μέσα στο dict αλλά αυτό ήδη υπάρχει
            # product_data['sku'] = sku
            sample_products.append(product_data)
            
            count += 1
            if count >= TARGET_RECORDS:
                break
                
        print(f"Downloaded  {len(sample_products)} records μέσω streaming.")

    finally:
        response.close()
        response.release_conn()

    # Μετατροπή σε αρχικό DataFrame
    df_products = pd.json_normalize(sample_products)
    print(f"DataFrame: Rows = {df_products.shape[0]}, Columns = {df_products.shape[1]}")
    df_products.head()

   


    # Στο πάνω κελί είχα μία λίστα η οποία είχε μέσα n sku, μαζί με όλα τα attributes τουσ.
    # Τώρα στο βήμα αυτό κάνω access την λίστα και απομονώνω σε ένα set μόνο τον κωδικό των n sku (η επιλογή set βασίζεται στην γρήγορη αναζήτηση)
    target_skus = {p['sku'] for p in sample_products}

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
            
            # Aπλά για να βεβαιωθώ ότι όσα products πήρα άλλες τόσες και οι τιμές 
            if len(terms_list) >= len(target_skus):
                break
                
        print(f"Downloaded {len(terms_list)} matching terms μέσω streaming.")

    finally:
        parser.close()
        parser.release_conn()


    df_terms = pd.DataFrame(terms_list)
    print(f"Terms DataFrame: Rows = {df_terms.shape[0]}, Columns = {df_terms.shape[1]}")
    df_terms.head()






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

    print(df_terms.columns)
    df_terms.head(2)







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

    print(f"Dimensions (rows,cols): {df_terms_final.shape}")
    df_terms_final.head()







    df_terms_final = df_terms_final.explode('appliesTo').reset_index(drop=True)

    print(f"Dimensions (rows,cols): {df_terms_final.shape}")
    df_terms_final.head()





    if 'termAttributes' in df_terms_final.columns:
        df_terms_final = df_terms_final.drop(columns=['termAttributes'])

    print (f"Dimension (rows,cols): {df_terms_final.shape}")
    df_terms_final.head()









    rowCount = len(df_terms_final)

    #Βάζω το if για να μπορώ να τρέχω το κελί και μόνο του χωρίς να πετάει error
    if 'skuNew' in df_terms_final.columns and 'sku' in df_terms_final.columns:

        # Φτιάχνω την συνθήκη ελέγχου - διαγραφής μιας υπηρεσίας και την εφαρμόζω απευθείας μετά πάνω στο dataframe. Γλιτώνω το loop 
        condition = (df_terms_final['skuNew'] == df_terms_final['sku'])

        df_filtered_terms = df_terms_final[condition]

        df_terms_final = df_filtered_terms.copy()

    print(f"Initial records: {rowCount}")
    print(f"Rejected records: {rowCount - len(df_terms_final)}")

    if 'skuNew' in df_terms_final.columns:
        df_terms_final = df_terms_final.drop(columns=['skuNew'])

    print(f"Dimensions (rows,cols): {df_terms_final.shape}")
    df_terms_final.head()







    if 'effectiveDate' in df_terms_final.columns:
        df_terms_final = df_terms_final.drop(columns=['effectiveDate'])

    print(f"Dimensions (rows,cols): {df_terms_final.shape}")
    df_terms_final.head()






    if 'beginRange' in df_terms_final.columns and 'endRange' in df_terms_final.columns:

        df_terms_final = df_terms_final[df_terms_final['beginRange'] == '0']

        df_terms_final.drop(columns=['beginRange', 'endRange'], inplace=True)

    df_terms_final.reset_index(drop=True, inplace=True)

    print(f"Dimensions (rows,cols): {df_terms_final.shape}")
    df_terms_final.head()







    df_terms_final['priceUSD'] = pd.to_numeric(df_terms_final['priceUSD'], errors='coerce')

    df_terms_final = df_terms_final[df_terms_final['priceUSD'] > 0]

    df_terms_final.reset_index(drop=True, inplace=True)

    print(f"Dimensions (rows,cols): {df_terms_final.shape}")
    df_terms_final.head()





    if 'appliesTo' in df_terms_final.columns:
        df_terms_final = df_terms_final[df_terms_final['appliesTo'].isna()]

        df_terms_final.reset_index(drop=True, inplace=True)

        df_terms_final.drop(columns=['appliesTo'], errors='ignore', inplace=True)

    print(f"Dimensions (rows,cols): {df_terms_final.shape}")
    df_terms_final.head()







    colsToCheck = ['sku', 'priceUSD', 'unit']
    df_terms_final.dropna(subset=colsToCheck, inplace=True)
    df_terms_final.reset_index(drop=True, inplace=True)






    if 'offerTermCode' in df_terms_final.columns:

        df_terms_final.drop(columns=['offerTermCode'], errors='ignore', inplace=True)

    print(f"Dimensions (rows,cols): {df_terms_final.shape}")








#Το pipeline για EC2 (Instances, Bare Metal, Storage & Extras)
def parse_ec2_compute(client):
    print()



#  Το pipeline για RDS (Instances, Storage, Extras)
def parse_rds():
    print ()




#Το pipeline για S3 (Storage Master & Operations Master)
def parse_s3():
    print() 



#Το pipeline για VPC (Ενιαίο Master)
def parse_vpc():
    print()





#Το pipeline για EKS (Ενιαίο Master με απευθείας JOIN)
def parse_eks():
    print ()



def run_aws_pipeline(client):

    df_terms, df_products = parse_ec2_compute(client=client)






def main():

    
    utils.set_up_logger()
    logging.info ("Starting azure pipeline execution")

    client = config.create_minio_client()
    logging.info ("Succesfully created client")

    if not utils.bucket_creation(client, config.PROVIDERS.get("azure").get("clean_bucket")):
        return


    run_aws_pipeline(client=client)



if __name__ == "__main__":
    main()