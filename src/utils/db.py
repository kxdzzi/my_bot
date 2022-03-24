from src.utils.config import config
from pymongo import MongoClient

mg_list = config.mongodb.get("mongdb_list")
mg_usr = config.mongodb.get("mongodb_username")
mg_pwd = config.mongodb.get("mongodb_password")


class DB():

    def __new__(cls, *args, **kwargs):
        '''单例'''
        if not hasattr(cls, '_instance'):
            orig = super(DB, cls)
            cls._instance = orig.__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self, db_name="my_bot"):
        """
        创建mongodb客户端
        """
        self.client = MongoClient(f'mongodb://{",".join(mg_list)}/',
                                  username=mg_usr,
                                  password=mg_pwd)
        self.db = self.client[db_name]

        # 机器人配置
        self.bot_conf = self.db.bot_conf
        # 机器人信息
        self.bot_info = self.db.bot_info
        # 群配置
        self.group_conf = self.db.group_conf
        # 群冷却时间配置
        self.group_cd_conf = self.db.group_cd_conf
        # 插件信息
        self.plugins_info = self.db.plugins_info
        # 用户信息
        self.user_info = self.db.user_info
        # 冷却时间记录
        self.search_record = self.db.search_record
        # 河灯
        self.river_lantern = self.db.river_lantern
        # 聊天记录
        self.chat_log = self.db.chat_log
        # 用户背包
        self.knapsack = self.db.knapsack
        # 江湖
        self.jianghu = self.db.jianghu
        # 装备
        self.equip = self.db.equip
        # npc
        self.npc = self.db.npc
        # 交易行
        self.auction_house = self.db.auction_house

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def insert_auto_increment(self, collection, data):
        _id = self.db.counters.find_one_and_update(
            filter={"_id": collection},
            update={"$inc": {"sequence_value": 1}},
            upsert=True
        )["sequence_value"]
        data.update(
            {"_id": _id}
        )
        self.db[collection].insert_one(data)
        return _id

    def close(self):
        if self.client:
            self.client.close()

db = DB()

if __name__ == "__main__":
    pass

