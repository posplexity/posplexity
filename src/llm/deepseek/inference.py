import requests, openai, tiktoken, os, json, base64, time
from src.utils.decorator import retry_async

prompt_base_path = "src/llm/deepseek/prompt"
client = openai.AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1",
)

async def async_run_deepseek(
    target_prompt: str,
    prompt_in_path: str,
    llm_model: str = "deepseek-chat",
) -> str:
    """
    deepseek chat 모델 사용 코드
    """

    # Load prompt
    with open(
        os.path.join(prompt_base_path, prompt_in_path), "r", encoding="utf-8"
    ) as file:
        prompt_dict = json.load(file)

    system_prompt = prompt_dict["system_prompt"]
    user_prompt_head, user_prompt_tail = (
        prompt_dict["user_prompt"]["head"],
        prompt_dict["user_prompt"]["tail"],
    )

    user_prompt_text = "\n".join([user_prompt_head, target_prompt, user_prompt_tail])
    input_content = [{"type": "text", "text": user_prompt_text}]

    chat_completion = await client.beta.chat.completions.parse(
        model=llm_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": input_content},
        ],
        # response_format=output_structure,
    )
    chat_output = chat_completion.choices[0].message.content
    return chat_output, chat_completion


@retry_async(max_attempts=3, delay_seconds=1, exceptions=(Exception,))
async def run_deepseek_stream(
    target_prompt: str,
    prompt_in_path: str,
    llm_model: str = "deepseek-chat",
):
    """
    deepseek chat 모델 사용 코드 (비동기 + 스트리밍)
    """
    # Load prompt
    with open(
        os.path.join(prompt_base_path, prompt_in_path), "r", encoding="utf-8"
    ) as file:
        prompt_dict = json.load(file)

    system_prompt = prompt_dict["system_prompt"]
    user_prompt_head, user_prompt_tail = (
        prompt_dict["user_prompt"]["head"],
        prompt_dict["user_prompt"]["tail"],
    )

    user_prompt_text = "\n".join([user_prompt_head, target_prompt, user_prompt_tail])
    input_content = [{"type": "text", "text": user_prompt_text}]

    stream = await client.chat.completions.create(
        model=llm_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": input_content},
        ],
        stream=True
    )

    return stream
