from PIL import Image
from io import BytesIO
from dotenv import load_dotenv

import requests, openai, os, json, base64

load_dotenv()

prompt_base_path = "src/llm/gpt/prompt"
client = openai.AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)


def encode_image(image_source):
    """
    이미지 경로가 URL이든 로컬 파일이든 Pillow Image 객체이든 동일하게 처리하는 함수.
    이미지를 열어 base64로 인코딩합니다.
    Pillow에서 지원되지 않는 포맷에 대해서는 예외를 발생시킵니다.
    """
    try:
        # 이미 Pillow 이미지 객체인 경우 그대로 사용
        if isinstance(image_source, Image.Image):
            image = image_source
        else:
            # URL에서 이미지 다운로드
            if isinstance(image_source, str) and (
                image_source.startswith("http://")
                or image_source.startswith("https://")
            ):
                response = requests.get(image_source)
                image = Image.open(BytesIO(response.content))
            # 로컬 파일에서 이미지 열기
            else:
                image = Image.open(image_source)

        # 이미지 포맷이 None인 경우 (메모리에서 생성된 이미지 등)
        if image.format is None:
            # logger.warning("Image format is None. Defaulting to JPEG.")
            image_format = "JPEG"
        else:
            image_format = image.format

        # 이미지 포맷이 지원되지 않는 경우 예외 발생
        if image_format not in Image.registered_extensions().values():
            raise ValueError(f"Unsupported image format: {image_format}.")

        buffered = BytesIO()
        # PIL에서 지원되지 않는 포맷이나 다양한 채널을 RGB로 변환 후 저장
        if image.mode in ("RGBA", "P", "CMYK"):  # RGBA, 팔레트, CMYK 등은 RGB로 변환
            image = image.convert("RGB")
        image.save(buffered, format="JPEG")

        return base64.b64encode(buffered.getvalue()).decode("utf-8")

    except requests.exceptions.RequestException as e:
        raise ValueError(f"Failed to download the image from URL: {e}")
    except IOError as e:
        raise ValueError(f"Failed to process the image file: {e}")
    except ValueError as e:
        raise ValueError(e)


async def async_run_gpt(
    target_prompt: str,
    prompt_in_path: str,
    output_structure,
    img_in_data: str = None,
    img_resolution: str = "high",
    gpt_model: str = "gpt-4o-mini",
) -> str:
    """
    이미지+텍스트 데이터에 대해 gpt 모델을 사용합니다.
    structured, step 등 beta 기능을 적용한 코드입니다.

    Args:
        target_prompt(str): Input data를 넣습니다. user_prompt_head와 user_prompt_tail 사이에 삽입됩니다.
        prompt_in_path(str): 각 task에 맞게 정리해둔 prompt(json)의 경로를 지정합니다.
        output_structure: output structure를 입력합니다.
        img_in_data(str): 이미지 데이터 경로, 혹은 Url을 넣습니다.
        gpt_model(str): 사용할 gpt 모델을 선택합니다. (gpt-4o-2024-08-06 / gpt-4o-mini)


    Returns:
        str: GPT를 통해 나온 final 결과를 반환합니다.
    """
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

    if img_in_data is not None:
        encoded_image = encode_image(img_in_data)
        input_content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{encoded_image}",
                    "detail": img_resolution,
                },
            }
        )

    chat_completion = await client.beta.chat.completions.parse(
        model=gpt_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": input_content},
        ],
        response_format=output_structure,
    )
    chat_output = chat_completion.choices[0].message.parsed

    return chat_output#, chat_completion

async def run_gpt_stream(
    target_prompt: str,
    prompt_in_path: str,
    img_in_data: str = None,
    img_resolution: str = "high", 
    gpt_model: str = "gpt-4o-mini",
):
    """
    이미지+텍스트 데이터에 대해 gpt 모델을 사용합니다.
    structured, step 등 beta 기능을 적용한 코드입니다.
    """
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

    if img_in_data is not None:
        encoded_image = encode_image(img_in_data)
        input_content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{encoded_image}",
                    "detail": img_resolution,
                },
            }
        )

    stream = await client.chat.completions.create(
        model=gpt_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": input_content},
        ],
        stream=True
    )

    return stream
