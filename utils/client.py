"""Модуль для работы с различными клиентами. Отвечает за сетевое взаимодействие."""
import aiohttp
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

from settings import YCOMBINATOR_BASE_URL


logger = logging.getLogger()


@dataclass
class Request:
    url: str
    method: str = "GET"
    headers: dict | None = None
    data: dict | None = None
    params: dict | None = None
    timeout: int = 10


class BaseClient(ABC):
    base_url: str
    success_statuses: tuple[int, int, int] = (200, 201, 203)

    @abstractmethod
    async def get(self, *args, **kwargs): ...


class RequestError(Exception):
    """Ошибка при запросе."""

    def __init__(self, *args, body: str | bytes | None = None, status_code: int | None = None):
        self.status_code = status_code
        self.body = body
        super().__init__(*args)


@dataclass
class YaClient(BaseClient):
    base_url: str = YCOMBINATOR_BASE_URL

    async def get(self, url, with_base: bool = False):
        url = self.full_url(url) if with_base else url
        req = Request(url=url)
        return await self._request(req)

    def full_url(self, url: str) -> str:
        return f'{self.base_url}{url}'

    async def _request(self, req: Request) -> bytes | None:
        _request_kwargs = {
            'method': req.method,
            'url': req.url,
            'headers': req.headers,
            'data': req.data,
            'params': req.params,
            'timeout': aiohttp.ClientTimeout(total=req.timeout)
        }

        logger.info('Request %s %s', req.method, req.url, extra=_request_kwargs)

        async with aiohttp.ClientSession() as client:
            resp: aiohttp.ClientResponse
            async with client.request(**_request_kwargs, ssl=False) as resp:  # type: ignore
                if resp.status not in self.success_statuses:
                    txt = await resp.content.read()
                    logger.error(
                        f'Request fail {req.method} {req.url} {resp.status}',
                    )
                    raise RequestError('Request fail', body=txt, status_code=resp.status)

                txt = await resp.read()
                logger.debug('Response %s', txt)

        return txt
