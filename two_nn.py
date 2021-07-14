import os
import json
import logging
import requests
import itertools

from collections import defaultdict
from bs4 import BeautifulSoup


LIMIT_LAST_100_COMMENTS = "/-100"
TWONN_URL = "https://www.2nn.jp/matsuri/s{}.html"
POST_PER_PAGE = 50

DESKTOP_AGENTS = itertools.cycle([
    {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'},
    {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:53.0) Gecko/20100101 Firefox/53.0'},
    {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.79 Safari/537.36 Edge/14.14393'},
    {'User-Agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1)'},
    {'User-Agent': 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.4506.2152; .NET CLR 3.5.30729)'},
    {'User-Agent': 'Mozilla/5.0 (compatible, MSIE 11, Windows NT 6.3; Trident/7.0; rv:11.0) like Gecko'}
])

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

    res = requests.get(url, headers=DESKTOP_AGENTS.__next__())
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
