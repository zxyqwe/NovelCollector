import os
import re
import logging
import argparse
import requests as rq
from pathlib import Path
from urllib.request import url2pathname
from bs4 import BeautifulSoup as soup

PWD = Path(os.path.realpath(__file__)).parent
CACHE_DIR = PWD / "cache"
CACHE_DIR.mkdir(exist_ok=True)
REQ_SESSION = rq.Session()


def get_pathname_from_url(url):
    invalid_char = [':', '.', '<', '>', '/', '\\', '|', ';', '*', '?', '&', ',']
    for idx in invalid_char:
        url = url.replace(idx, "_")
    return url


def download_file(dst, src):
    if dst.exists():
        return
    ret = REQ_SESSION.get(src)
    if ret.status_code != 200:
        logger.error(f"Download fail: {src}")
        ret.raise_for_status()
        return
    with dst.open('wb') as f:
        f.write(ret.content)
    logger.info(f"Download and Save: {src}")


def check_novel(main_url):
    cache_file = CACHE_DIR / get_pathname_from_url(main_url)
    if not cache_file.exists():
        download_file(cache_file, main_url)
    with cache_file.open() as f:
        page = soup(f, "lxml")

    # for test, we want get format like:
    # <a href="\d*.html" title=".*">

    def tag_feature_filter(tag):
        return tag.name == 'a' and tag.has_attr('href') and tag.has_attr('title')

    chapter_path = []
    for tag in page.find_all(tag_feature_filter):
        chapter_path.append(tag["href"])
    root_path = url2pathname(main_url)
    logger.info(f"Root Path: {root_path}")

    for idx in chapter_path:
        join_url = root_path + idx
        cache_file = CACHE_DIR / get_pathname_from_url(join_url)
        if not cache_file.exists():
            download_file(cache_file, join_url)
        with cache_file.open() as f:
            page = soup(f, "lxml")
        print("\n\t".join(page.stripped_strings))
        exit()


def set_log_if_start_from_this_file():
    LOG_FORMAT = '[%(asctime)s] [%(levelname)1.1s] %(message)s'
    formatter = logging.Formatter(LOG_FORMAT)

    # global logger accept all logs of this program
    global_logger = logging.getLogger('novel')
    # filter of level DEBUG
    global_logger.setLevel(logging.DEBUG)
    # do not report log to root level to avoid unexpected action
    # e.g., conda environment
    global_logger.propagate = False

    # log to console (screen), level INFO, use the format template
    log_to_console = logging.StreamHandler()
    log_to_console.setLevel(logging.INFO)
    log_to_console.setFormatter(formatter)
    global_logger.addHandler(log_to_console)


if __name__ == "__main__":
    set_log_if_start_from_this_file()
    logger = logging.getLogger('novel.main')
    logger.info("Start from main.py")
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--url", help="Main Page of the Novel Website", type=str)
    args = parser.parse_args()
    if args.url:
        check_novel(args.url)
    else:
        logger.error("Do Nothing!")
