import os
import json
import logging
import requests

from collections import defaultdict
from bs4 import BeautifulSoup


LIMIT_LAST_100_COMMENTS = "/-100"
TWONN_URL = "https://www.2nn.jp/matsuri/s{}.html"
POST_PER_PAGE = 50


logging.basicConfig(
    filename="std.log",
    format="%(asctime)s %(message)s",
    filemode="w"
)

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


def crawl(page):
    logger.info(f"Start crawl {page}~{page+POST_PER_PAGE} article")
    articles_in_page = defaultdict(list)

    url = TWONN_URL.format(page)
    res = requests.get(url)
    if res.status_code != 200:
        logger.warning(f"fail: {url}")
        return

    soup = BeautifulSoup(res.text, "html5lib")
    articles_wrapper = soup.select(".news4plus article ol li")
    for article in articles_wrapper:
        pubtime_dom = article.find("time")
        pubdatetime = pubtime_dom["datetime"]
        pubdate = pubdatetime.split(" ")[0]

        title_dom = article.select("h2>a")
        title = title_dom[0].text
        article_url = title_dom[0]["href"]
        article_content, article_response = get_5ch_content(article_url)

        if not article and not article_response:
            continue

        out = {
            "pubdatetime": pubdatetime,
            "url": article_url,
            "title": title,
            "content": article_content,
            "response": article_response,
        }
        articles_in_page[pubdate].append(out)
    logger.info(f"Finish Crawl {page}~{page+POST_PER_PAGE} article")
    save(articles_in_page)


def save(articles_grouped_by_date):
    logger.info("Save to file")
    data_dir = "data"
    for pubdate, articles in articles_grouped_by_date.items():
        filename = f"{pubdate}.json"
        file_path = os.path.join(data_dir, filename)
        write_mode = "a" if os.path.exists(file_path) else "w"
        with open(file_path, write_mode, encoding="utf8") as f:
            json.dump(articles, f)
            f.write(os.linesep)
    logger.info("Saving done")


def get_5ch_content(url):
    # show all without paging
    if url.endswith(LIMIT_LAST_100_COMMENTS):
        url = url.replace(LIMIT_LAST_100_COMMENTS, "")

    res = requests.get(url)
    if res.status_code != 200:
        logger.warning(f"fail open 5chn: {url}")
        return None, None

    soup = BeautifulSoup(res.text, "html5lib")

    if _is_dl_dd_structure(soup):
        postes = soup.select("dl.thread dd")
    else:
        postes = soup.select(".post .message")

    if not postes:
        logger.warning(f"Can't get posts from {url}")
        return None, None

    postes_text = [post.text for post in postes]
    content = postes_text[0]
    responses = postes_text[1:] if len(postes_text) > 1 else []

    return content, responses


def _is_dl_dd_structure(soup):
    '''
    https://daily.5ch.net/test/read.cgi/newsplus/1490788389/
    https://hayabusa8.5ch.net/test/read.cgi/mnewsplus/1490290133/
    https://hayabusa3.5ch.net/test/read.cgi/mnewsplus/1413290238/
    '''
    return soup.find("body").get("bgcolor") == "#efefef"

if __name__ == "__main__":
    logger.info("Start cawling")
    for page in range(1, 30000 + 1, POST_PER_PAGE):
        try:
            crawl(page)
        except Exception as e:
            logger.exception(e)
    logger.info("Crawling finished")
