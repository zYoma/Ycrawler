import asyncio
import logging

import settings
from utils.crawler import Ycrawler


logger = logging.getLogger()


async def main():
    crawler = Ycrawler()
    while True:
        logger.info('crawler start process')
        await crawler.start()
        logger.info('crawler end process')
        await asyncio.sleep(settings.PAUSE_BETWEEN_REQUESTS)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname).1s %(message)s',
        datefmt='%Y.%m.%d %H:%M:%S',
    )
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        ...
