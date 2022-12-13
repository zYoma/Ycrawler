from typing import Any

import asyncio
import logging

from .client import BaseClient, YaClient
from .parser import BaseParser, Link, YParser


logger = logging.getLogger()


class Ycrawler:

    def __init__(self):
        self.urls: set = set()
        self.client: BaseClient = YaClient()
        self.parser: BaseParser = YParser()

    async def get_index_links(self) -> list[Link]:
        #  Обрабатываем и получаем все ссылки с главной страницы
        index_page = await self.client.get('/', with_base=True)
        return self.parser.parse_index_page(index_page)

    async def get_comment_links(self, links: list[Link]) -> None:
        # Для всех ссылок парим страницы с комментариями и сохраняем ссылки в атрибуте links CommentLink
        for link in links:
            comment = link.comment_link
            comment.links = self.parser.parse_comment_page(comment.html)

    def get_new_links(self, index_links: list[Link]):
        #  Для определения новых ссылок, приводим полученные ссылки к множеству.
        index_urls_set = set([link.url for link in index_links])
        #  Возвращаем те, что есть в множестве index_urls_set, но нет в self.urls.
        new_urls = index_urls_set ^ self.urls
        new_links = [link for link in index_links if link.url in new_urls]
        return new_urls, new_links

    async def _concurrent_requests(self, urls: list[str]):
        # собираем список коорутин для конкурентного исполнения
        tasks = [self.client.get(url) for url in urls]
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def get_site_link_html(self, links: list[Link]) -> None:
        htmls = await self._concurrent_requests([link.url for link in links])
        # каждому объекту link присваиваем значение атрибута html
        [setattr(link, 'html', html) for link, html in zip(links, htmls)]  # type: ignore

    async def get_comment_sub_link_html(self, links: list[Link]) -> list[tuple[str, Any]]:
        results = []
        for link in links:
            comment_links = link.comment_link.links
            htmls = await self._concurrent_requests([url for url in comment_links])  # type: ignore
            results.append((link.file_name, htmls))

        return results

    async def get_comment_page_links(self, links: list[Link]) -> None:
        comment_htmls = await self._concurrent_requests([link.comment_link.url for link in links])
        # полученные результаты присваиваем атрибуту html у CommentLink
        [setattr(link.comment_link, 'html', html) for link, html in zip(links, comment_htmls)]  # type: ignore

    async def start(self):
        index_links = await self.get_index_links()
        new_urls, new_links = self.get_new_links(index_links)
        logger.info(f'find {len(new_urls)} new links')
        #  Дополняем множество self.urls новыми ссылками.
        self.urls |= new_urls

        await self.get_site_link_html(new_links)
        # конкурентно сохраняем сайты
        await asyncio.gather(*[self.parser.save_site_links(link) for link in new_links])
        await self.get_comment_page_links(new_links)
        await self.get_comment_links(new_links)
        comment_sites_data_for_save = await self.get_comment_sub_link_html(new_links)
        # для каждого сайта, сохраняем вложенные сайты со страницы комментариев
        for parent_dir, data in comment_sites_data_for_save:
            await asyncio.gather(
                *[self.parser.save_comment_links(html, parent_dir, str(n)) for n, html in enumerate(data)],
            )
