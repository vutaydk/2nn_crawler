from datetime import datetime
import logging
from collections import defaultdict
import requests
from bs4 import BeautifulSoup

logging.basicConfig(filename="std.log", 
					format='%(asctime)s %(message)s', 
					filemode='w')
logger=logging.getLogger() 
logger.setLevel(logging.DEBUG) 

TWONN_URL = "https://www.2nn.jp/matsuri/s{}.html"
POST_PER_PAGE = 50

def crawl(page):
        logger.info(f"Start crawl {page}~{page+POST_PER_PAGE} article")
        articles_in_page = defaultdict(list)

        url = TWONN_URL.format(page)
        res = requests.get(url)
        if res.status_code !=200:
            logger.warning(f"fail: {url}")
            return
        
        soup = BeautifulSoup(res.text, "html5lib")
        articles_wrapper = soup.select(".news4plus article ol li")
        i =0 
        for article in articles_wrapper:
            i +=1
            if i == 2:
                break
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
                "response": article_response
            }
            articles_in_page[pubdate].append(out)
        logger.info(f"Finish Crawl {page}~{page+POST_PER_PAGE} article")
        save(articles_in_page)

import os
import json
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



    
LIMIT_LAST_100_COMMENTS = "/-100"
def get_5ch_content(url):
    #show all without paging
    if url.endswith(LIMIT_LAST_100_COMMENTS):
        url.replace(LIMIT_LAST_100_COMMENTS, "")

    res = requests.get(url)
    if res.status_code != 200:
        logger.warning(f"fail open 5chn: {url}")
        return None, None

    soup = BeautifulSoup(res.text, "html5lib")
    postes = soup.select(".post .message")
    postes_text = [post.text for post in postes]
    return postes_text[0], postes_text[1:]

if __name__ == "__main__":
    logger.info("Start cawling")
    for page in range(1, 30000+1, POST_PER_PAGE):
        try:
            crawl(page)
        except Exception as e:
            logger.exception(e)
    logger.info("Crawling finished")