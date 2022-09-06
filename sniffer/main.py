import time
import requests
import urllib3
import json
import pymongo

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Sniffer:
    def __init__(self, config_file):
        with open(config_file) as f:
            self.config = json.loads(f.read())
        self.token_index = 0
        self.headers_template = {'Accept': 'application/vnd.github+json', 'Connection': 'close', 'Authorization': ''}
        self.proxy = {'https': 'http://192.168.89.1:7890'}  # 根据实际情况判断是否需要代理,不需要则直接注释该行,并将下一行取消注释
        # self.proxy = None
        self.client = pymongo.MongoClient(self.config["mongodb"])  # 链接mongodb
        self.client = self.client["github"]  # mongodb 数据库名

    def mongodb_check_repository(self, repository):
        col = self.client["main"]  # main 表名
        return col.find_one({"repository": repository}) is None

    def mongodb_check_path(self, repository, branch, path):
        col = self.client[repository]  # 仓库名 表名
        return col.find_one({"branch": branch, "path": path}) is None

    def mongodb_check_subquery(self, repository):
        col = self.client["main"]
        return col.find_one({"repository": repository, "subquery": False}) is None

    def check_blacklist(self, content, blacklist):
        for word in self.config["blacklist"][blacklist]:
            if word in content:
                return True
        return False
        # pattern = "|".join(self.config['blacklist'][blacklist])
        # return re.search(pattern, content) is not None

    def githubapi(self, url):
        headers = self.headers_template
        while True:
            headers['Authorization'] = "token {}".format(self.config['token'][self.token_index % len(self.config['token'])])
            self.token_index += 1
            try:
                r = requests.get(url=url, proxies=self.proxy, headers=headers)
            except requests.exceptions.SSLError:
                time.sleep(1)
                continue
            except requests.exceptions.ProxyError:
                time.sleep(1)
                continue
            else:
                result = r.json()
                if 'message' in result.keys():
                    print(time.time(), result['message'])
                    if 'Only the first 1000 search results are available' in result['message']:
                        return None
                    time.sleep(60)
                    continue
                else:
                    break
        return result

    def subquery(self, repository):
        if self.mongodb_check_subquery(repository):
            return
        for keyword in self.config['subquery']:
            page = 1
            while True:
                url = "https://api.github.com/search/code?q=repo:{} {}&sort=indexed&per_page={}&page={}".format(repository, keyword, self.config["per_page"], page)
                result = self.githubapi(url)
                if result is None:
                    break
                for item in result['items']:
                    branch = item['url'][-40:]
                    path = item['path']
                    ext = path.lower().split('.')[-1]
                    if ext == 'js' or ext == 'htm' or ext == 'html' or ext == 'css' or ext == 'license':  # 屏蔽js/css/html/license文件
                        continue
                    if self.mongodb_check_path(repository, branch, path):
                        col = self.client[repository]
                        col.insert_one({"branch": branch, "keyword": keyword, "path": path, "url": item['html_url'], "mark": False})
                        print(keyword, repository, branch, path)
                if page * self.config["per_page"] < result['total_count']:
                    page += 1
                    continue
                else:
                    break
        col = self.client["main"]
        col.update_one({"repository": repository}, {"$set": {"subquery": True}})

    def query(self, keyword, size):
        for language in self.config['languages']:
            page = 1
            while True:
                url = "https://api.github.com/search/code?q={} language:{} size:{}..{}&sort=indexed&per_page={}&page={}".format(keyword, language, size * 1000, (size + 5) * 1000, self.config["per_page"], page)
                result = self.githubapi(url)
                if result is None:
                    break
                for item in result['items']:
                    branch = item['url'][-40:]
                    repository = item['repository']['full_name']
                    description = item['repository']['description']
                    path = item['path']
                    raw = 'https://raw.githubusercontent.com/' + repository + '/' + branch + '/' + path
                    if item['repository']['fork'] or self.check_blacklist(repository.lower(), 'repository') or self.check_blacklist(path.lower(), 'path'):
                        continue
                    if description is None:
                        pass
                    elif self.check_blacklist(description.lower(), 'description'):
                        continue
                    while True:
                        try:
                            r = requests.get(url=raw, proxies=self.proxy)
                        except requests.exceptions.SSLError:
                            time.sleep(1)
                            continue
                        except requests.exceptions.ProxyError:
                            time.sleep(1)
                            continue
                        else:
                            if r.status_code == 200:
                                content = r.text
                                break
                    if self.check_blacklist(content.lower(), 'content'):
                        continue
                    if keyword not in content.lower():
                        continue
                    if self.mongodb_check_repository(repository):
                        col = self.client["main"]
                        col.insert_one({"repository": repository, "subquery": False, "mark": False})
                    if self.mongodb_check_path(repository, branch, path):
                        col = self.client[repository]
                        col.insert_one({"branch": branch, "keyword": keyword, "path": path, "url": item['html_url'], "mark": False})
                        print("default", keyword, repository, branch, path)
                        self.subquery(repository)
                if page * self.config["per_page"] < result['total_count']:
                    page += 1
                    continue
                else:
                    break


if __name__ == '__main__':
    sniffer = Sniffer('config.json')

    with open('target.txt') as f:
        targets = f.read().splitlines()
    for size in range(0, 300, 5):  # 仅查询0-300KB之间的文件,每5KB作为一次查询分割,300KB的限制是因为https://code.jquery.com/jquery-3.6.1.js的大小在300KB左右
        for target in targets:
            sniffer.query(target, size)
