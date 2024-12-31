from openai import OpenAI, AsyncOpenAI

client = OpenAI()
async_client = AsyncOpenAI()

def openai_embedding(target_text:str, embedding_model:str="text-embedding-3-large"):
    response = client.embeddings.create(
        input=target_text,
        model=embedding_model
    )
    return response.data[0].embedding

async def async_openai_embedding(target_text:str, embedding_model:str="text-embedding-3-large"):
    response = await async_client.embeddings.create(
        input=target_text,
        model=embedding_model
    )
    return response.data[0].embedding 