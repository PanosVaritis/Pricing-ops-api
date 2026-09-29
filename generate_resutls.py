import pandas as pd
import io
import sys
import os

current = os.path.dirname(__file__)
path_to_root = os.path.join(current, '..')
abs_path = os.path.abspath(path_to_root)
sys.path.append(abs_path)
import config
import utils
import logging

def collect_clean_bucket_metrics(client):

    clean_buckets = {
        "AWS": config.PROVIDERS.get("aws").get("clean_bucket"),
        "Azure": config.PROVIDERS.get("azure").get("clean_bucket"),
        "GCP": config.PROVIDERS.get("google").get("clean_bucket")
    }

    metrics_list = []

    logging.info("Starting collection of metrics from clean buckets...")

    for provider, bucket_name in clean_buckets.items():
        if not bucket_name:
            logging.warning(f"Bucket name for {provider} is not defined in config.")
            continue

        try:
            objects = client.list_objects(bucket_name, recursive=True)
            
            for obj in objects:
                object_name = obj.object_name
                
  

                logging.info(f"Processing object: {object_name} from {provider} bucket ({bucket_name})")

                response = client.get_object(bucket_name, object_name)
                try:
                    file_bytes = response.read()
                    file_size_mb = len(file_bytes) / (1024 * 1024) # Μετατροπή σε MB

                    df = pd.read_csv(io.BytesIO(file_bytes))
                    row_count = df.shape[0]
                    col_count = df.shape[1]

                    metrics_list.append({
                        'Provider': provider,
                        'File_Name': object_name,
                        'Rows': row_count,
                        'Columns': col_count,
                        'Size_MB': round(file_size_mb, 4)
                    })

                except Exception as parse_err:
                    logging.error(f"Error parsing file {object_name}: {parse_err}")
                finally:
                    response.close()
                    response.release_conn()

        except Exception as bucket_err:
            logging.error(f"Error accessing bucket {bucket_name} for {provider}: {bucket_err}")

    df_metrics = pd.DataFrame(metrics_list)
    return df_metrics

def main():
    utils.set_up_logger()
    logging.info("Starting metrics generation script execution")

    client = config.create_minio_client()
    logging.info("Successfully created MinIO client")

    df_results = collect_clean_bucket_metrics(client)

    if not df_results.empty:
        print("\n" + "="*80)
        print("Metrics array for clean data")
        print("="*80)
        print(df_results.to_string(index=False))
        print("="*80 + "\n")
        
    else:
        logging.warning("No metrics were collected. Check bucket contents or connections.")

if __name__ == "__main__":
    main()