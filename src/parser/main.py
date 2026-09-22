import requests
import os, sys
current = os.path.dirname(__file__)
path_to_root = os.path.join (current, '../..')
abs_path = os.path.abspath(path_to_root)
sys.path.append(abs_path)
import config
from minio.error import S3Error
import pandas as pd
object_name = "Kubernetes_Engine/page_1.json"  
client = config.create_minio_client()
import logging
import utils
import aws_parser
import google_parser
import azure_parser
import shutil




def main():
    try:

        print ("-" * shutil.get_terminal_size().columns)

        utils.set_up_logger()

        print ("-" * shutil.get_terminal_size().columns)
        logging.info("Running script to injest data from providers")
        print ("-" * shutil.get_terminal_size().columns)

        azure_parser.main()

        print ("-" * shutil.get_terminal_size().columns)
        google_parser.main()

        print ("-" * shutil.get_terminal_size().columns)
        aws_parser.main()

        print ("-" * shutil.get_terminal_size().columns)

    except KeyboardInterrupt:
        logging.info("Execution interrupted by user.")

    except Exception :
        logging.exception ("Error while running data cleaning  script ")

    


if __name__ == "__main__":
    main()