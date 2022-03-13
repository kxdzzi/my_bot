from typing import Union
import os
import yaml


class Config():
    '''配置文件类'''

    def __new__(cls, *args, **kwargs):
        '''单例'''
        if not hasattr(cls, '_instance'):
            orig = super(Config, cls)
            cls._instance = orig.__new__(cls, *args, **kwargs)
        return cls._instance

    def __getattr__(self, item) -> dict[str, Union[str, int, bool]]:
        '''获取配置'''
        value = self._config.get(item)
        if value:
            return value
        raise AttributeError("未找到该配置字段，请检查config.yml文件！")

    def __init__(self):
        '''初始化'''
        root_path = os.path.realpath(__file__+"/../../../")
        config_file = os.path.join(root_path, "config.yml")
        with open(config_file, 'r', encoding='utf-8') as f:
            cfg = f.read()
            self._config: dict = yaml.load(cfg, Loader=yaml.FullLoader)

        # 创建目录
        path: dict = self._config.get('path')

        # data文件夹
        data: str = path.get('data')
        datadir = os.path.join(root_path, data)
        if not os.path.isdir(datadir):
            os.makedirs(datadir)

        # log文件夹
        logs: str = path.get('logs')
        logsdir = os.path.join(root_path, logs)
        if not os.path.isdir(logsdir):
            os.makedirs(logsdir)


config = Config()
'''项目配置文件'''
