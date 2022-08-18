# GithubSniffer

一个简陋的Github信息采集工具(主要用于hvv/渗透测试时的单次信息采集,不建议作为长期资产监控的工具)

> 2022.8.18

1.0版本发布,采集端使用`Python`配合`Github API`进行采集,WEB端使用`Flask`和`jquery+bootstrap`进行交互

2.0版本预计将采集端使用`Golang`进行进行重写,WEB端使用`Gin-Vue-Admin`进行交互,提高效率

# 使用方法

## 采集端

1. `pip install -r requirement.txt`

2. 配置`config.json`

`mongodb`填入`mongodb`的链接字符串

`token`填入要使用的`Github Token`

>不建议使用自己的Github帐号的Token去进行采集,容易封号(:

[https://github.com/settings/tokens](https://github.com/settings/tokens)

![](https://img.mi3aka.eu.org/2022/08/51e0511cc4666bfc95bba01f6c87dd46.png)

只需要勾选`repo-public_repo`即可,建议配置5个不同账号的token以保证效率

`languages`和`extensions`为要采集的语言特征,可自行修改

`blacklist`为黑名单,包括用户名/仓库名/路径/文件内容黑名单,可自行修改

`subquery`为项目内的子查询,用于快速定位项目中的敏感信息,可自行修改

`per_page`为`Github API`单次采集的数量,无特殊需要保持默认即可,最大值为`100`

3. 根据需要调整`sniffer/main.py`中的`self.proxy`和`self.client`中的数据库名

4. 将需要进行采集的域名放入`target.txt`

5. `python3 main.py`

## WEB端

1. `pip install -r requirement.txt`

2. 配置`config.json`,与采集端的配置相同即可

`mongodb`填入`mongodb`的链接字符串

`token`填入要使用的`Github Token`

3. 根据需要调整`web/app.py`中的`proxy`和`client`中的数据库名

4. `python3 -m flask run --host=0.0.0.0`

![](https://img.mi3aka.eu.org/2022/08/93e3f4e704bcd5a71480555e0f70b7fa.png)

# 项目构成

## 采集端

采集端使用mongodb作为数据库,结构如下

> 数据库名/main

| _id | mark | repository | subquery |
|:---:|:----:|:----------:|:--------:|
| _id | 是否标记 |    仓库名     | 是否完成子查询  |

> 数据库名/仓库名

| _id | branch | mark | keyword | path | url |
|:---:|:------:|:----:|:-------:|:----:|:---:|
| _id |   分支   | 是否标记 |   关键词   | 文件路径 | URL |

1. 调用token进行批量采集,并进行黑名单过滤
2. 将过滤后的仓库写入`数据库名/main`中
3. 在当前仓库中进行关键词检索(子查询)如`token password apikey`等
4. 将检索结果写入`数据库名/仓库名`中

## WEB端

`Flask`作为数据库查询的API,`bootstrap+jquery`进行渲染,前后端交互的js为`web/static/js/scripts.js`(写得很烂,能跑就行