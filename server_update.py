# coding=utf-8

from wsgiref.simple_server import make_server

import hmac
import os
import yaml

root_path = os.path.realpath(__file__+"/../")


config_file = os.path.join(root_path, "config.yml")
with open(config_file, 'r', encoding='utf-8') as f:
    cfg = f.read()
    config = yaml.load(cfg, Loader=yaml.FullLoader)

github_conf = config.get("github")
github_secret = github_conf.get('secret')
port = github_conf.get('port')


def encryption(data):
    key = github_secret.encode('utf-8')
    obj = hmac.new(key, msg=data, digestmod='sha1')
    return obj.hexdigest()


def application(environ, start_response):
    print("收到github webhook, 开始验证...")
    start_response('200 OK', [('Content-Type', 'text/html')])
    request_body = environ["wsgi.input"].read(
        int(environ.get("CONTENT_LENGTH", 0)))
    token = encryption(request_body)
    signature = environ.get("HTTP_X_HUB_SIGNATURE").split('=')[-1]
    print(f"{token:}")
    print(f"{signature:}")
    if token != signature:
        print("验证失败")
        return "token 验证失败"
    print("开始更新...")
    os.system(f'sh {root_path}/restart_mybot.sh')
    print("更新成功!")
    return [b'Hello, webhook!']


def listen_github_hook():
    # 创建一个服务器，IP地址为空，端口是8000，处理函数是application:
    httpd = make_server('', port, application)
    print(f'Serving HTTP on port {port}...')
    # 开始监听HTTP请求:
    httpd.serve_forever()


if __name__ == "__main__":
    listen_github_hook()
