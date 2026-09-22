import os
import sys
import shutil
import logging



# -------------------------------------------------------------
# ΡΥΘΜΙΣΗ PATHS (Για να βλέπει τη ρίζα /code/ και το /code/src/)
# -------------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__)) # /code/src/

# 1. Πηγαίνουμε έναν φάκελο πίσω (/code/) για να βρούμε το utils.py
root_dir = os.path.abspath(os.path.join(current_dir, '..'))
if root_dir not in sys.path:
    sys.path.append(root_dir)

# 2. Ο φάκελος src/ (current_dir) για να βλέπει τα injestion & parser
if current_dir not in sys.path:
    sys.path.append(current_dir)

# -------------------------------------------------------------
# IMPORTS
# -------------------------------------------------------------
import utils  # Τώρα το βρίσκει από το /code/utils.py!

from injestion.main import main as run_ingestion_main
from parser.main import main as run_parser_main

def main():
    try:

        print ("-" * shutil.get_terminal_size().columns)

        utils.set_up_logger()

        print ("-" * shutil.get_terminal_size().columns)
        logging.info("Running completed pipeline")
        print ("-" * shutil.get_terminal_size().columns)

        run_ingestion_main()

        print ("-" * shutil.get_terminal_size().columns)
        run_parser_main()

     
    except KeyboardInterrupt:
        logging.info("Execution interrupted by user.")

    except Exception :
        logging.exception ("Error while running data cleaning  script ")

    


if __name__ == "__main__":
    main()

