# Multi-Cloud FinOps Data Pipeline (GCP, AWS, Azure)

This project is a pipeline of ingestion, cleaning and alignemnt of cloud pricing data from the three major cloud service providers: **Google (GCP)**, **Amazon (AWS)**, and **Azure**. 
The final goal of the project is the automated extraction of raw pricing data given from the providers and after major cleaning and other processes the the imposition of a common format for the purpose of providing third parties for finops analysis

---

## Project folder structure 

The project can either be executed seperate at each step (Injestion, Parser) for a specific provider or as a whole. 

```text
📂 code/
│                
├── 📄 config.py                 # Settings to connect to minio and provider urls
├── 📄 requirements.txt          # Libraries used for the framework
├── 📄 .env                      # Credentials of user
├── 📄 .gitignore               
├── 📄 docker-compose.yml        
├── 📄 utils.py                  # Utility functions (ex: logger init)
├── 📂 src
├── 📂 notebooks
│
├── 📂 src/injestion/            # Injest raw data from provider and store in minio
│   ├── 📄 google_data.py        # Standalone injestion for google
│   ├── 📄 azure_data.py         # Standalone injestion for azure
|   ├── 📄 aws_data.py           # Standalone injestion for aws
│   └── 📄 main.py               # Orchestrator for combined injestion from all providers
│
├── 📂 src/parser/               # Clean raw data and store in new buckets in minio
│   ├── 📄 google_parser.py      # Standalone cleaning for google
│   ├── 📄 azure_parser.py       # Standalone cleaning for azure        
│
└── 📂 notebooks/                # Study data structure
    ├── 📄 google_eda.ipynb      # Study google json schema
    └── 📄 azure_eda.ipynb       # Study azure json schema 
```
# Installation
1. Clone repository to your local machine and enter base folder
```bash
git clone https://github.com/PanosVaritis/Pricing-ops-api.git
cd code/
```
2. Create a virtual environment using conda or venv (conda is used below)
```bash
conda create -- env_name python=3.10
conda activate env_name
```
3. Install all the requirements using pip
```bash
pip install --uprade pip
pip install -r requirements.txt
```
4. Create a .env and set up your credentials
```bash
touch .env
```
The .env should look like the below. No quotes required
```bash
MINIO_ROOT_USER=your_minio_username
MINIO_ROOT_PASSWORD=your_minio_password
GOOGLE_API_KEY=your_google_api_key
```
5. Create your google api key
```bash
- Enter google cloud console and select project (or create new)
- Api & services -> Credentials -> Create Credentials -> Api Key
```

# Execution
1. Always before execution activate the container
```bash 
docker compose up
```
2. Running ingestion code

All scripts together (requires an hour)
```bash
python src/injestion/main.py
```
Seperate for each provider
```bash
python src/injetsion/providername_data.py
```
3. Running parser code (Only google for time being)
```bash
python src/parser/google_parser.py
```