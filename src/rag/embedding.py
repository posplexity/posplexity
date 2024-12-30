from openai import OpenAI
client = OpenAI()

def openai_embedding(target_text:str, embedding_model:str="text-embedding-3-large"):
    response = client.embeddings.create(
        input=target_text,
        model=embedding_model
    )
    return response.data[0].embedding