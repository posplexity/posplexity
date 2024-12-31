
import functools, time, traceback, asyncio


def retry(max_attempts=3, delay_seconds=1, exceptions=(Exception,)):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempts += 1
                    time.sleep(delay_seconds)
                    if attempts == max_attempts:
                        raise

        return wrapper

    return decorator


def retry_async(max_attempts=3, delay_seconds=1, exceptions=(Exception,)):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_attempts:
                try:
                    return await func(*args, **kwargs)  # 비동기 함수 실행
                except exceptions as e:
                    attempts += 1
                    await asyncio.sleep(delay_seconds)  # 비동기 함수 대기
                    if attempts == max_attempts:
                        raise

        return wrapper

    return decorator
