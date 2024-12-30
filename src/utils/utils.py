import os
import requests
import asyncio
from urllib.parse import urlparse
from typing import Optional

def download_file(url: str, save_dir: Optional[str] = None, default_filename: str = "temp_downloaded.docx") -> str:
    """
    URL에서 파일을 다운로드하여 저장하고 저장된 파일의 경로를 반환합니다.

    Args:
        url (str): 다운로드할 파일의 URL
        save_dir (str, optional): 파일을 저장할 디렉토리 경로. 기본값은 None (현재 디렉토리)
        default_filename (str, optional): URL에서 파일명을 추출할 수 없을 때 사용할 기본 파일명

    Returns:
        str: 저장된 파일의 전체 경로

    Raises:
        requests.exceptions.RequestException: URL 다운로드 실패시
        OSError: 파일 저장 실패시
    """
    try:
        # URL에서 파일 다운로드
        response = requests.get(url, timeout=15)
        response.raise_for_status()

        # URL에서 파일명 추출
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)
        
        # 파일명이 없으면 기본 파일명 사용
        if not filename:
            filename = default_filename

        # 저장 디렉토리 설정
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
            file_path = os.path.join(save_dir, filename)
        else:
            file_path = filename

        # 파일 저장
        with open(file_path, "wb") as f:
            f.write(response.content)

        return file_path

    except requests.exceptions.RequestException as e:
        raise Exception(f"파일 다운로드 실패: {str(e)}")
    except OSError as e:
        raise Exception(f"파일 저장 실패: {str(e)}")
    


async def async_wrapper(tasks: list) -> list:
    """
    여러 비동기 작업을 비동기 함수 내에서 실행하는 함수입니다.

    Args:
        tasks (List[Coroutine]): 실행할 비동기 작업의 리스트

    Returns:
        list: 모든 비동기 작업의 결과를 포함한 리스트
    """
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # 이미 실행 중인 이벤트 루프가 있는 경우
        return await asyncio.gather(*tasks)
    else:
        # 새로운 이벤트 루프를 생성하는 경우
        return asyncio.run(asyncio.gather(*tasks))