import requests
from bs4 import BeautifulSoup
import time
import os
from itertools import count
import shutil
import argparse
import pathlib
import urllib.parse
from requests.exceptions import RequestException


class CustomCrawler:
    def __init__(self,
                 url,
                 depth=1,
                 sleep=1,
                 path='./'):
        self.depth = depth
        self.url = url
        self.sleep = sleep
        self.found_urls_set_tmp = set()
        self.cur_id_tmp = 0
        self.path = path
        self.data_path = path + '/data'

    def write_url(self, url_id, url):
        """Writes urls into urls.txt"""
        with open(f'{self.path}/urls.txt', 'a') as f:
            f.write(str(url_id) + ' ' + url + '\n')
        return

    def save_html(self, url_id, content):
        """Saves html files into ..data/ dir"""
        with open(f"{self.data_path}/{url_id}.html", 'wb+') as f:
            f.write(content)
        return

    def proper_url(self, url, parent_url):
        """
        Makes absolute url from relative if necessary
        """
        parent_scheme = urllib.parse.urlsplit(parent_url).scheme
        parent_netlock = urllib.parse.urlsplit(parent_url).netloc
        root_page = parent_scheme + '://' + parent_netlock
        try:
            if urllib.parse.urlsplit(url).netloc == '':
                if url[0] == '/':
                    return urllib.parse.urljoin(root_page, url)
                # if not: it is not typical for this site relative link on '/htmlcss/..' pages
                else:
                    split_parent_url = parent_url.split('/')[:-1]
                    return split_parent_url[0] + '//' + '/'.join(split_parent_url[1:])[1:] + '/' + url
            else:
                return url
        except:
            print("Unexpeted url format, not sure if url is valid.",
                  f"URL: {url} from {parent_url}",
                  sep='\n'
                  )
            return -1

    def check_external_urls(self, url):
        """
        Checks if url leads to external site
        """
        if urllib.parse.urlsplit(url).netloc == urllib.parse.urlsplit(self.url).netloc:
            return url
        else:
            return -1

    def get_urls(self, url, depth, parent_url=None):
        """
        Main class method.
        Recursively searches through a site's urls and dowloads htmls.
        """
        if depth > 0:
            # pause for not being banned
            self.cur_id_tmp += 1
            time.sleep(self.sleep)

            # checking requests errors
            try:
                response = requests.get(url)
            except (RequestException, ConnectionError) as request_error:
                if self.cur_id_tmp == 1:
                    print(f"Request exception with initial url {url}:",
                          f"Error info: {request_error}",
                          "Make sure if url is specified correctly (e.g. https://younglinux.info)",
                          sep='\n'
                          )
                    return
                else:
                    print(f"Request exception with url {url} from page {parent_url}:",
                          f"Error info: {request_error}",
                          "This page will not be saved",
                          sep='\n'
                          )
                    return

            # checking status code
            # decided not to save pages with error codes like 404. they are useless
            if response.status_code != 200:
                if self.cur_id_tmp == 1:
                    print(f"Wrong status code ({str(response.status_code)}) from initial url {url}",
                          "Make sure if url is specified correctly (e.g. https://younglinux.info/bash/linuxhistory)",
                          sep='\n'
                          )
                    return
                else:
                    print(f"Wrong response status code ({str(response.status_code)}) \
                    with url {url} from page {parent_url}")
                    print("Expected 200. This page will not be saved")
                    return

            # some additional informing message 
            if self.cur_id_tmp == 1:
                print("Initial page was reached successfully.")
                print(f"""Starting parsing {self.url}...\n\nResults will be availble in {self.path}""")

            tree = BeautifulSoup(response.content, 'html.parser')

            links = []
            for i in tree.findAll('a'):
                proper_url_response = self.proper_url(i.get('href'), parent_url=url)
                if proper_url_response != -1:
                    link = proper_url_response
                if self.check_external_urls(link) != -1:
                    links.append(link)

            # dropping self-links
            links = list(filter(lambda x: x != url, links))

            # dropping duplicates and already saved urls
            links = list(set(links).difference(self.found_urls_set_tmp))

            # adding new urls for checking in next iterations
            self.found_urls_set_tmp = self.found_urls_set_tmp.union(links)

            self.write_url(url_id=self.cur_id_tmp, url=url)

            self.save_html(url_id=self.cur_id_tmp, content=response.content)

            # recursive search through found urls
            for link in links:
                self.get_urls(url=link, depth=depth - 1, parent_url=url)
        else:
            return

    def parse(self):
        """
        Creates or cleares data/ folder and urls.txt file
        And then executes a parsing process
        """
        # creating folder for html files (clearing if exists)
        if not os.path.exists(self.data_path):
            os.makedirs(self.data_path)
        else:
            shutil.rmtree(self.data_path)
            os.makedirs(self.data_path)
            # clearing urls.txt if exists
        with open(f'{self.path}/urls.txt', 'w') as f:
            f.truncate(0)
        self.get_urls(url=self.url, depth=self.depth)
        print("Parsing process finished.")
        return


# cmd arguments
parser = argparse.ArgumentParser(
    description="""Recursive downloading of pages on pointed url.
    With depth > 1 script saves html from internal links on page.
    """,
)
parser.add_argument(
    'url',
    help="""url of the site ("https://..")""",
    type=str
)
parser.add_argument(
    '-d',
    help="depth of search (default=1)",
    type=int,
    default=2
)
parser.add_argument(
    '-s',
    help="pauses between requests to site (in seconds)",
    type=float,
    default=0.5
)
parser.add_argument(
    '-p',
    help="path to save results",
    type=str,
    default="./"
)

# parsing arguments from command line
args = parser.parse_args()
url = args.url
depth = args.d
sleep = args.s
path = os.path.abspath(args.p)
CustomCrawler(url=url, depth=depth, sleep=sleep, path=path).parse()
