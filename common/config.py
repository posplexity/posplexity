# Common
DEFAULT_CHUNK_SIZE = 1000 
DEFAULT_CHUNK_STEP = 500    
MAX_CHUNK_LENGTH = 1000
EMBED_BATCH_SIZE = 200

# Deprecated
COLLECTION_NAME_EXP = "posplexity-demo-local"
COLLECTION_NAME_PROD = "posplexity-demo"

# Postech
POSTECH_COLLECTION_PROD = "posplexity-postech-prod"
POSTECH_COLLECTION_EXP = "posplexity-postech-exp"
POSTECH_BUCKET_NAME = "posplexity-postech"
POSTECH_REGION_NAME = "us-east-1"

# Kaist
KAIST_COLLECTION_PROD = "posplexity-kaist-prod"
KAIST_COLLECTION_EXP = "posplexity-kaist-exp"

COLLECTION_NAME = {
    "postech": {
        "prod": POSTECH_COLLECTION_PROD,
        "exp": POSTECH_COLLECTION_EXP
    },
    "kaist": {
        "prod": KAIST_COLLECTION_PROD,
        "exp": KAIST_COLLECTION_EXP 
    }
}