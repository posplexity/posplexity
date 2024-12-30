import os

QDRANT_CONFIG = QdrantConfig(
    # url=os.getenv("QDRANT_URL"),
    host=os.getenv("QDRANT_HOST"),
    port=os.getenv("QDRANT_PORT"),
    prefix="inven",
    api_key=os.getenv("QDRANT_API_KEY"),
)

QDRANT_


