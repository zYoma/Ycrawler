"""Модуль для парсинга и записи данных на диск."""
import aiofiles
from abc import ABC, abstractmethod
from aiofiles import os
from bs4 import BeautifulSoup
from dataclasses import dataclass

from settings import BASE_LINKS_DIR, YCOMBINATOR_BASE_URL


@dataclass
class CommentLink:
    url: str
    html: str | bytes | None = None
    links: list[str] | None = None


@dataclass
class Link:
    url: str
    comment_link: CommentLink
    html: str | bytes | None = None

    @property
    def file_name(self):
        return self.url.split('/')[2]


class BaseParser(ABC):
    base_url: str

    @abstractmethod
    def parse_index_page(self, *args, **kwargs) -> list[Link]: ...

    @abstractmethod
    def parse_comment_page(self, *args, **kwargs) -> list[str]: ...

    @abstractmethod
    def save_site_links(self, *args, **kwargs): ...

    @abstractmethod
    def save_comment_links(self, *args, **kwargs): ...


class YParser(BaseParser):
    base_url: str = YCOMBINATOR_BASE_URL

    def parse_index_page(self, html: bytes) -> list[Link]:
        soup = BeautifulSoup(html, 'lxml')
        # находим все tr с новостными ссылками
        tr_list = soup.find_all('tr', class_='athing')
        results = []
        for tr in tr_list:
            # для каждой ссылки получаем id и формируем ссылку на комментарии
            tr_id = tr.get('id')
            comment_url = f'{self.base_url}/item?id={tr_id}'
            # парсим ссылку на саму новость
            url = tr.find('span', class_='titleline').find('a').get('href')
            # для внутренних ссылок добавляем базовую часть
            if not url.startswith('http'):
                url = f'{self.base_url}/{url}'
            # cоздаем экземпляр Link
            link = Link(url=url, comment_link=CommentLink(url=comment_url))
            results.append(link)

        return results

    def parse_comment_page(self, html: bytes) -> list[str]:
        if not isinstance(html, bytes):
            return []

        soup = BeautifulSoup(html, 'lxml')
        # ищем все span с комментариями
        comment_spans = soup.find_all('span', class_='commtext c00')

        urls = []
        for span in comment_spans:
            # собираем все ссылки внутри span
            links = span.find_all('a')
            for link in links:
                # получаем href каждой ссылки
                url = link.get('href')
                urls.append(url)

        return urls

    async def save_site_links(self, link: Link) -> None:
        if isinstance(link.html, bytes):
            dir_name = link.file_name
            file_name = link.file_name
            dir_path = f'{BASE_LINKS_DIR}/{dir_name}'
            await self._save_file(link.html, dir_path, file_name)

    async def save_comment_links(self, html: bytes, parent_dir: str, file_name: str) -> None:
        if isinstance(html, bytes):
            dir_name = file_name
            dir_path = f'{BASE_LINKS_DIR}/{parent_dir}/{dir_name}'
            await self._save_file(html, dir_path, file_name)

    @staticmethod
    async def _save_file(html: bytes, dir_path: str, file_name: str) -> None:
        await os.makedirs(dir_path, exist_ok=True)
        async with aiofiles.open(f'{dir_path}/{file_name}.html', mode='wb') as f:
            await f.write(html)
