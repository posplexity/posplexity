from urllib.parse import urlparse
from typing import Optional
from botocore.exceptions import ClientError
from tqdm import tqdm

import os, requests, asyncio, boto3


def download_file(url: str, save_dir: Optional[str] = None, default_filename: str = "temp_downloaded.docx") -> str:
    """
    URL에서 파일을 다운로드하여 저장하고 저장된 파일의 경로를 반환합니다.
    """
    try:
        # 1. URL에서 파일 다운로드
        response = requests.get(url, timeout=15)
        response.raise_for_status()

        # 2. URL에서 파일명 추출
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)
        
        # 파일명이 없으면 기본 파일명 사용
        if not filename:
            filename = default_filename

        # 3. 저장 디렉토리 설정
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
            file_path = os.path.join(save_dir, filename)
        else:
            file_path = filename

        # 4. 파일 저장
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
    """
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # 이미 실행 중인 이벤트 루프가 있는 경우
        return await asyncio.gather(*tasks)
    else:
        # 새로운 이벤트 루프를 생성하는 경우
        return asyncio.run(asyncio.gather(*tasks))



def upload_s3(files:list, access_key:str, secret_key:str, region_name:str, bucket_name:str, prefix:str=""):
    s3 = boto3.client(
        "s3",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region_name
    )

    # 전체 파일 개수 기준으로 tqdm Progress Bar 생성
    with tqdm(total=len(files), desc="파일 업로드 중", unit="개") as pbar:
        for file in files:
            # prefix가 있으면 파일명 앞에 추가
            file_key = os.path.join(prefix, file.name) if prefix else file.name
            file_bytes = file.read()
            file_size_mb = len(file_bytes) / (1024 * 1024)  # MB 단위 크기

            try:
                s3.put_object(
                    Bucket=bucket_name,
                    Key=file_key,
                    Body=file_bytes
                )
                # 업로드 후, tqdm에 파일명과 크기 정보를 Postfix로 표시
                pbar.set_postfix({
                    "File": file_key,
                    "Size(MB)": f"{file_size_mb:.2f}"
                })
            except ClientError as e:
                pbar.write(f"업로드 실패: {file_key}, 에러: {e}")

            # 한 파일 처리 완료 후 1만큼 업데이트
            pbar.update(1)

def list_s3_objects(bucket_name:str, region_name:str, access_key:str, secret_key:str, prefix:str=None) -> list:
    """
    S3 버킷 내 특정 prefix(폴더) 경로의 파일(Key) 목록을 반환.
    prefix가 None이면, 버킷 전체 목록을 반환.
    """
    s3 = boto3.client(
        "s3",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region_name
    )

    existing_files = []
    # prefix가 None 또는 빈 문자열이면 전체 목록
    list_kwargs = {"Bucket": bucket_name}
    if prefix:
        list_kwargs["Prefix"] = prefix

    response = s3.list_objects_v2(**list_kwargs)
    if "Contents" in response:
        existing_files = [obj["Key"] for obj in response["Contents"]]
    
    return existing_files



def generate_presigned_url(bucket_name, region_name, access_key, secret_key, file_key, expiration=36000):
    """
    S3 객체에 접근할 수 있는 Presigned URL을 생성하여 반환합니다.
    expiration(초 단위) 동안 유효합니다 (기본: 3600초 = 1시간).
    """
    s3 = boto3.client(
        "s3",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region_name
    )
    try:
        url = s3.generate_presigned_url(
            ClientMethod='get_object',
            Params={'Bucket': bucket_name, 'Key': file_key},
            ExpiresIn=expiration
        )
        return url
    except ClientError as e:
        print(f"Presigned URL 생성 실패: {e}")
        return None