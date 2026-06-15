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


"""
Virtual Machines belongs to family Compute
Storage belongs to family Storage
SQL Database belongs to family Databases
Azure Kubernetes Service belongs to family Compute
Virtual Network belongs to family Networking 
Bandwidth belongs to family Netwotking
"""


#This is filtering based on serviceName and not based on serviceFamily
SERVICE_NAME = ["Virtual Machines", "Storage", "SQL Database"]

TYPE = ["DevTestConsumption", "Reservation", "Consumption"]
