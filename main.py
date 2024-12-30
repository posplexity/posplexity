import asyncio
from src.deepseek.inference import run_deepseek_stream, async_run_deepseek
from src.gpt.inference import run_gpt_stream
import os

async def chat_loop():
    print("DeepSeek 챗봇을 시작합니다. 종료하려면 'quit' 또는 'exit'를 입력하세요.")
    
    # 간단한 대화를 위한 기본 프롬프트 설정
    chat_prompt_path = "chat_basic.json"  # 기본 대화용 프롬프트 파일
    output_structure = {"type": "text"}   # 일반 텍스트 응답 형식
    
    while True:
        # 사용자 입력 받기
        user_input = input("\n사용자: ").strip()
        
        # 종료 조건 확인
        if user_input.lower() in ['quit', 'exit']:
            print("챗봇을 종료합니다.")
            break
            
        try:
            # DeepSeek API 호출
            response = await run_gpt_stream(
                target_prompt=user_input,
                prompt_in_path=chat_prompt_path,
            )
            
            print("\n챗봇:", response)
            
        except Exception as e:
            print(f"\n오류가 발생했습니다: {str(e)}")

if __name__ == "__main__":
    asyncio.run(chat_loop())
