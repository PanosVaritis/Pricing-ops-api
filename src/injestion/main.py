import os 
import sys
import logging


#Since code is executed from main only here those imports are required
current = os.path.dirname(__file__)
path_to_root = os.path.join (current, '../..')
abs_path = os.path.abspath(path_to_root)
sys.path.append(abs_path)
import utils

import azure_data
import google_data
import aws_data



def main():
    try:
        utils.set_up_logger()
        logging.info("Running script to injest data from providers\n")
        azure_data.main()
        print ()
        aws_data.main()
        print()
        google_data.main()
        print()

    except Exception as e:
        logging.error ("Error ")


if __name__ == "__main__":
    main()