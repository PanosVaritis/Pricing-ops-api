import os 
import sys
import logging


#Since code is executed from main only here those imports are required
current = os.path.dirname(__file__)
path_to_root = os.path.join (current, '../..')
abs_path = os.path.abspath(path_to_root)
sys.path.append(abs_path)
import utils
import shutil

import azure_data
import google_data
import aws_data



def main():
    try:

        print ("-" * shutil.get_terminal_size().columns)

        utils.set_up_logger()

        print ("-" * shutil.get_terminal_size().columns)
        logging.info("Running script to injest data from providers")
        print ("-" * shutil.get_terminal_size().columns)

        azure_data.main()

        print ("-" * shutil.get_terminal_size().columns)
        aws_data.main()

        print ("-" * shutil.get_terminal_size().columns)
        google_data.main()

        print ("-" * shutil.get_terminal_size().columns)



    except KeyboardInterrupt:
        logging.info("Execution interrupted by user.")

    except Exception :
        logging.exception ("Error while running ingestion script ")



if __name__ == "__main__":
    main()





    
