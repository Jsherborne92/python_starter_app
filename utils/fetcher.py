import asyncio
from typing import Type, TypeVar, Generic, Optional, Dict
from pydantic import BaseModel, ValidationError
import httpx
from utils.logger import Logger

logger = Logger.init("fetcher", save_to_file=True)

T = TypeVar("T", bound=BaseModel)

BACK_OFF = 1
MAX_RETRIES = 5


class ApiFetcher(Generic[T]):
    def __init__(self, model: Type[T], base_url: str, headers: Optional[Dict[str, str]] = None, timeout=30):
        self.model = model
        self.base_url = base_url
        self.headers = headers or {}
        self.max_retries = MAX_RETRIES
        self.backoff = BACK_OFF
        self.timeout = timeout

    async def fetch(self, endpoint: str, **params) -> T:
        for i in range(self.max_retries):
            logger.debug(f"Fetching {endpoint} with params {params}")
            try:
                async with httpx.AsyncClient(headers=self.headers, timeout=self.timeout) as client:
                    response = await client.get(f"{self.base_url}{endpoint}", params=params)
                    response.raise_for_status()
                    try:
                        json_response = response.json()
                        logger.success(f"Successfully fetched {endpoint} with params {params}")
                        validated_data = self.model.validate(json_response)
                        return validated_data
                    except ValidationError as e:
                        logger.error(f"Endpoint: {endpoint} - Validation error for model {self.model.__name__}: {e}")
                    except ValueError:
                        logger.error(f"Failed to decode JSON from response - endpoint: {endpoint}")
            except (httpx.ReadTimeout, httpx.RemoteProtocolError, httpx.ReadError, httpx.ConnectError, httpx.HTTPStatusError, httpx.HTTPError) as e:
                if i == self.max_retries - 1:
                    logger.error(f"Request failed with error: {e}. Endpoint: {endpoint}. Params: {params}. Max retries exceeded.")
                    raise e
                logger.warning(f"Request failed with error: {e}. Endpoint: {endpoint}. Params: {params}. ...retrying.")
                await asyncio.sleep(self.backoff)
                self.backoff *= 2
        raise Exception("Max retries exceeded.")

    async def post(self, endpoint: str, **params) -> T:
        for i in range(self.max_retries):
            logger.debug(f"Posting {endpoint} with params {params}")
            try:
                async with httpx.AsyncClient(headers=self.headers) as client:
                    response = await client.post(f"{self.base_url}{endpoint}", json=params)
                    response.raise_for_status()
                    try:
                        json_response = response.json()
                        validated_data = self.model.validate(json_response)
                        return validated_data
                    except ValidationError as e:
                        logger.error(f"Validation error for model {self.model.__name__}: {e}")
                    except ValueError:
                        logger.error("Failed to decode JSON from response")
            except (httpx.ReadTimeout, httpx.RemoteProtocolError, httpx.HTTPStatusError, httpx.HTTPError) as e:
                if i == self.max_retries - 1:
                    logger.error(f"Request failed with error: {e}. Endpoint: {endpoint}. Params: {params}. Max retries exceeded.")
                    raise e
                logger.warning(f"Request failed with error: {e}. Endpoint: {endpoint}. Params: {params}. ...retrying.")
                await asyncio.sleep(self.backoff)
                self.backoff *= 2
        raise Exception("Max retries exceeded.")
