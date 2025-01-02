from src.utils.decorator import retry_async
import openai, os, json

prompt_base_path = "src/llm/prompt"
async_client = openai.AsyncOpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

client = openai.OpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)


def run_gemini(
    target_prompt: str,
    prompt_in_path: str,
    llm_model: str = "gemini-2.0-flash-exp",
) -> str:
    """
    gemini 모델 사용 코드
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

    chat_completion = client.beta.chat.completions.parse(
        model=llm_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": input_content},
        ],
    )
    chat_output = chat_completion.choices[0].message.content
    return chat_output, chat_completion

async def async_run_gemini(
    target_prompt: str,
    prompt_in_path: str,
    llm_model: str = "gemini-2.0-flash-exp",
) -> str:
    """
    gemini 모델 사용 코드
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

    chat_completion = await async_client.beta.chat.completions.parse(
        model=llm_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": input_content},
        ],
    )
    chat_output = chat_completion.choices[0].message.content
    return chat_output, chat_completion


@retry_async(max_attempts=3, delay_seconds=1, exceptions=(Exception,))
async def run_gemini_stream(
    target_prompt: str,
    prompt_in_path: str,
    llm_model: str = "gemini-2.0-flash-exp",
):
    """
    gemini 모델 사용 코드 (비동기 + 스트리밍)
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

    stream = await async_client.chat.completions.create(
        model=llm_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": input_content},
        ],
        stream=True
    )

    return stream
