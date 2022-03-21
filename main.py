import os
import logging
import argparse
import re
import requests as rq
from ebooklib import epub
from pathlib import Path
from urllib.request import url2pathname
from urllib.parse import urljoin
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
    page_title = page.title.get_text()

    # for test, we want get format like:

    # def tag_feature_filter(tag):
    #     # <a href="\d*.html" title=".*">
    #     return tag.name == 'a' and tag.has_attr('href') and tag.has_attr('title') and tag["href"].endswith(".html")

    def tag_feature_filter(tag):
        # <a href="\d*.html">
        return tag.name == 'a' and tag.has_attr('href') and re.match(r".*\d+\.html", str(tag["href"]), re.I) is not None

    chapter_path = []
    for tag in page.find_all(tag_feature_filter):
        chapter_path.append(tag["href"])
    chapter_path = sorted(list(set(chapter_path)))
    root_path = url2pathname(main_url)
    logger.info(f"Root Path: {root_path}")

    ch_list = []
    for idx in chapter_path:
        join_url = urljoin(root_path, idx)
        cache_file = CACHE_DIR / get_pathname_from_url(join_url)
        if not cache_file.exists():
            download_file(cache_file, join_url)
        with cache_file.open() as f:
            page = soup(f, "lxml")
        title = page.title.get_text()
        main_content = page.find("div", id="content")
        main_content = "<p>" + "</p><p>".join([idx.replace("\n", "") for idx in main_content.stripped_strings]) + "</p>"

        # write one chapter
        epub_link = idx
        if epub_link.find("/") >= 0:
            epub_link = epub_link[epub_link.find("/") + 1:]
        tmp_ch = epub.EpubHtml(title=title, file_name=epub_link)
        tmp_ch.set_content(f"<h1>{title}</h1>" + str(main_content))
        ch_list.append(tmp_ch)

        logger.info(f"Handle: {cache_file}")

    book = epub.EpubBook()
    book.set_title(page_title)
    book.set_language('zh')
    for idx in ch_list:
        book.add_item(idx)
    nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content='''
@namespace epub "http://www.idpf.org/2007/ops";
body {
    font-family: Cambria, Liberation Serif, Bitstream Vera Serif, Georgia, Times, Times New Roman, serif;
}
h2 {
     text-align: left;
     text-transform: uppercase;
     font-weight: 200;
}
ol {
        list-style-type: none;
}
ol > li:first-child {
        margin-top: 0.3em;
}
nav[epub|type~='toc'] > ol > li > ol  {
    list-style-type:square;
}
nav[epub|type~='toc'] > ol > li > ol > li {
        margin-top: 0.3em;
}
''')
    book.add_item(nav_css)
    book.toc = ch_list
    book.spine = ['nav', *ch_list]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    output_file = cache_file.with_suffix(".epub")
    epub.write_epub(output_file, book)
    logger.info(f"Generate: {output_file}")


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
