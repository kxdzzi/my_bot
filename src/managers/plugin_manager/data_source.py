from typing import Literal, Optional

from nonebot.plugin import get_loaded_plugins
from src.utils.db import db


async def get_bot_enable(bot_id: int):
    bot_info = db.bot_info.find_one({"_id": bot_id})
    return bool(bot_info and bot_info.get("enable"))


async def get_plugin_status(group_id: int, module_name: str) -> Optional[bool]:
    '''获取插件状态'''
    _con = db.plugins_info.find_one({'_id': group_id})
    if not _con:
        return None
    return _con.get(module_name, {}).get("status")


async def get_bot_status(group_id: int) -> Optional[bool]:
    '''获取机器人开启情况'''
    _con = db.group_conf.find_one({'_id': group_id})
    if not _con:
        return None
    return _con.get("group_switch")


def _chinese_to_bool(string: Literal["打开", "关闭"]) -> bool:
    '''将开关解析为bool'''
    return (string == "打开")


async def change_group_config(group_id: int, config_type: str, status: Literal["打开", "关闭"]) -> bool:
    '''
    :说明
        改变群设置

    :参数
        * group_id：QQ群号
        * config_type：开关类型
        * status：开关

    :返回
        * bool：如果有设置，则成功，没有改设置会返回False
    '''
    type_dic = {
        "进群通知": "welcome_status",
        "离群通知": "someoneleft_status",
        "开服推送": "ws_server",
        "新闻推送": "ws_news",
        "奇遇推送": "ws_serendipity",
        "抓马监控": "ws_horse",
        "扶摇监控": "ws_fuyao",
    }
    if config_type not in type_dic:
        return False
    db.group_conf.update_one({'_id': group_id}, {'$set': {
        type_dic[config_type]: _chinese_to_bool(status)
    }}, True)
    return True


async def change_plugin_status(group_id: int, plugin_name: str, status: Literal["打开", "关闭"]) -> bool:
    '''
    :说明
        改变插件开关

    :参数
        * group_id：QQ群号
        * plugin_name：插件名称
        * status：开关

    :返回
        * bool：如果有设置，则成功，没有改设置会返回False
    '''
    flag = False
    module_name = ""
    plugins = list(get_loaded_plugins())
    for one_plugin in plugins:
        export = one_plugin.export
        _plugin_name = export.get("plugin_name")
        if _plugin_name == plugin_name:
            flag = True
            module_name = one_plugin.name
    if flag:
        module_info = {}
        _con = db.plugins_info.find_one({"_id": group_id})
        if _con:
            module_info = _con.get(module_name, {})
        module_info.update({"status": _chinese_to_bool(status)})
        db.plugins_info.update_one({'_id': group_id}, {'$set': {
            module_name: module_info
        }}, True)
    return True
