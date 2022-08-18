from flask import Flask, request, render_template
import urllib3
import requests
import time
import pymongo
import json
import bson

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
app = Flask(__name__)
proxy = {'https': 'http://192.168.89.1:7890'}
# proxy = None
config_file = 'config.json'
with open(config_file) as f:
    config = json.loads(f.read())
client = pymongo.MongoClient(config["mongodb"])  # 链接mongodb
client = client["github"]  # mongodb 数据库名


@app.route('/')
def index():
    return render_template('index.html')


@app.route("/status")
def status():
    status, tokens = get_status()
    return {'status': status, 'tokens': tokens}


def get_status():
    url = 'https://api.github.com/rate_limit'
    headers_template = {'Accept': 'application/vnd.github+json', 'Connection': 'close', 'Authorization': ''}
    tokens = config['token']
    status = []
    for token in tokens:
        headers = headers_template
        headers['Authorization'] = "token {}".format(token)
        while True:
            try:
                r = requests.get(url=url, headers=headers, proxies=proxy)
            except requests.exceptions.SSLError:
                time.sleep(1)
                continue
            except requests.exceptions.ProxyError:
                time.sleep(1)
                continue
            else:
                result = r.json()
                break
        status.append(result)
    return status, tokens


@app.route("/repo")
def repo():
    col = client["main"]
    results = col.find()
    repos = dict()
    for result in results:
        repos[str(result['_id'])] = [result['repository'], result['mark']]
    return repos


@app.route("/detail", methods=['GET'])
def detail():
    id = request.args.get('id')[8:]
    detail = get_detail(id)
    return {'detail': detail}


def get_detail(id):
    col = client["main"]
    result = col.find_one({"_id": bson.objectid.ObjectId(id)})
    repo = result['repository']
    col = client[repo]
    results = col.find()
    detail = []
    for result in results:
        detail.append({"_id": str(result['_id']), "branch": result['branch'], "keyword": result['keyword'], "mark": result['mark'], "path": result['path'], "url": result['url']})
    return detail


@app.route("/delete", methods=['GET'])
def delete():
    if request.args.get('repo') is not None:
        repo = request.args.get('repo')[6:]
        col = client["main"]
        col.delete_one({"_id": bson.objectid.ObjectId(repo)})
    elif request.args.get('file') is not None:
        repo, file = request.args.get('file')[14:].split('|')
        col = client["main"]
        repo = col.find_one({"_id": bson.objectid.ObjectId(repo)})['repository']
        col = client[repo]
        col.delete_one({"_id": bson.objectid.ObjectId(file)})
    else:
        pass
    return {}


@app.route("/mark", methods=['GET'])
def mark():
    if request.args.get('repo') is not None:
        repo = request.args.get('repo')[4:]
        col = client["main"]
        mark = col.find_one({"_id": bson.objectid.ObjectId(repo)})['mark']
        col.update_one({"_id": bson.objectid.ObjectId(repo)}, {"$set": {"mark": not mark}})
    elif request.args.get('file') is not None:
        repo, file = request.args.get('file')[12:].split('|')
        col = client["main"]
        repo = col.find_one({"_id": bson.objectid.ObjectId(repo)})['repository']
        col = client[repo]
        mark = col.find_one({"_id": bson.objectid.ObjectId(file)})['mark']
        col.update_one({"_id": bson.objectid.ObjectId(file)}, {"$set": {"mark": not mark}})
    else:
        pass
    return {}
