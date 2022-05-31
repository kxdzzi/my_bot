from datetime import datetime
from src.utils.config import config
import time
from nonebot import Bot
from nonebot.plugin import get_loaded_plugins
from src.utils.db import db
from . import _jx3_event as Event


async def load_plugins(group_id: int):
    '''给某个群默认加载插件'''
    # 注册过的不再注册
    _con = db.plugins_info.find_one({'_id': group_id})
    if not _con:
        _con = {}
    # 注册所有插件
    plugins = list(get_loaded_plugins())
    for one_plugin in plugins:
        export = one_plugin.export
        plugin_name = export.get("plugin_name")
        if plugin_name is None:
            continue
        if _con.get(one_plugin.name, ""):
            continue
        db.plugins_info.update_one({'_id': group_id}, {
            '$set': {
                one_plugin.name: {
                    "module_name": one_plugin.name,
                    "plugin_name": plugin_name,
                    "command": export.get("plugin_command"),
                    "usage": export.get("plugin_usage"),
                    "status": export.get("default_status")
                },
            }
        }, True)


async def check_group(group_id: int, bot: Bot):
    """检查群是否活跃"""
    if group_id in config.bot_conf.get("manage_group", []):
        return
    con = db.group_conf.find_one({"_id": group_id})
    last_sent = None
    if con:
        last_sent = con.get("last_sent")
    if not last_sent:
        db.group_conf.update_one({
            "_id": group_id,
        }, {"$set": {
            "last_sent": datetime.now()
        }}, True)
        return
    if (datetime.now() - last_sent).days > 5:
        msg = "都五天没人跟我玩了，我还是走了吧。盈尺江湖，有缘再会！"
        db.group_conf.update_one({'_id': group_id}, {'$set': {
            "bot_id": 0
        }}, True)
        await bot.send_group_msg(group_id=group_id, message=msg)
        time.sleep(0.5)
        await bot.set_group_leave(group_id=group_id, is_dismiss=False)


async def register_bot(bot: Bot):
    bot_id = int(bot.self_id)

    ret = await bot.get_stranger_info(user_id=bot_id, no_cache=False)
    bot_name = ret['nickname']
    global BOT_NAME_MAP
    BOT_NAME_MAP[bot_id] = bot_name
    db.bot_info.update_one({"_id": bot_id}, {
        "$set": {
            "online_status": True,
            "bot_name": bot_name,
            "node_name": config.node_info.get("node"),
            "node_domain": config.node_info.get("domain"),
            "login_data": datetime.now()
        }
    }, True)


async def get_server(group_id: int) -> str:
    '''获取绑定服务器'''
    _con = db.group_conf.find_one({'_id': group_id})
    if _con:
        return _con.get("server", "")


async def get_ws_status(group_id: int, event: Event.RecvEvent) -> bool:
    '''
    :说明
        获取ws通知开关，robot为关闭时返回False

    :参数
        * group_id：QQ群号
        * event：接收事件

    :返回
        * bool：ws通知开关
    '''
    _con = db.group_conf.find_one({'_id': group_id})
    if not _con or not _con.get("group_switch", False):
        return False

    if isinstance(event, Event.ServerStatusEvent):
        recv_type = "ws_server"
    if isinstance(event, Event.NewsRecvEvent):
        recv_type = "ws_news"
    if isinstance(event, Event.SerendipityEvent):
        recv_type = "ws_serendipity"
    if isinstance(event, Event.HorseRefreshEvent) or isinstance(
            event, Event.HorseCatchedEvent):
        recv_type = "ws_horse"
    if isinstance(event, Event.FuyaoRefreshEvent) or isinstance(
            event, Event.FuyaoNamedEvent):
        recv_type = "ws_fuyao"
    if _con:
        return _con.get(recv_type, False)
