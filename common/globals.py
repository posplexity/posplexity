

from qdrant_client import QdrantClient
from transformers import AutoModel, AutoProcessor
from FlagEmbedding import BGEM3FlagModel
import os


qdrant_client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
)


def load_clip(clip_model_path: str) -> tuple[AutoModel, AutoProcessor]:
    """
    fashion-clip 모델을 로드합니다.

    Returns:
        (model_clip, processor_clip)
    """
    model_clip = AutoModel.from_pretrained(
        pretrained_model_name_or_path=clip_model_path, trust_ㅇㄷㄱremote_code=True
    )

    processor_clip = AutoProcessor.from_pretrained(
        pretrained_model_name_or_path=clip_model_path, trust_remote_code=True
    )

    return model_clip, processor_clip


def load_bgem3(device: str = "cpu") -> BGEM3FlagModel:
    """
    BGE-M3 model을 불러옵니다.
    """
    bgem3_model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True, device=device)

    return bgem3_model
