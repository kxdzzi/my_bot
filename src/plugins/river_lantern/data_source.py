import random
import datetime

from httpx import AsyncClient
from idna import check_initial_combiner
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from src.utils.cooldown_time import search_record, search_once
from src.utils.db import db
from src.utils.log import logger
from src.utils.browser import browser
from src.utils.email import mail_client

client = AsyncClient()
'''异步请求客户端'''


async def sent_river_lantern(
    user_id: int,
    user_name: str,
    类型: str,
    content: str,
) -> Message:
    '''
    :说明
        放河灯

    :参数
        * user_id：用户QQ
        * content：河灯内容
        * user_name：用户名

    :返回
        * Message：机器人返回消息
    '''
    if user_id in db.bot_conf.find_one({
            '_id': 1
    }).get("river_lantern_black_list", []):
        return ""
    app_name = "放河灯"
    # 查看冷却时间
    n_cd_time = 60
    flag, cd_time = await search_record(user_id, app_name, n_cd_time)
    if not flag:
        msg = f"[{app_name}] 冷却 > [{cd_time}]"
        return msg
    _con = db.user_info.find_one({'_id': user_id})
    gold = 0
    if _con:
        gold = _con.get("gold", 0)
    if gold < 5:
        logger.debug(f"<y>{user_id}</y> | <r>河灯金币不足</r>")
        ret_msg = '投放河灯需要五两银子，你没那么多银两！'
        return ret_msg

    if 类型 == "回复河灯":
        河灯id, content = content
        con = db.river_lantern.find_one({"_id": int(河灯id)})
        if not con:
            return "找不到你要回复的河灯"
        回复内容 = con["content"]
        回复昵称 = con["user_name"]
        你的回复 = content
        content += f"//{回复昵称}：{回复内容}"
        if len(content) > 512:
            content = "//".join(content[:512].split("//")[:-1])

    await search_once(user_id, app_name)
    river_lantern = db.user_info.find_one_and_update(
        filter={'_id': user_id},
        update={'$inc': {"gold": -5, "river_lantern": 1}},
        upsert=True).get("river_lantern", 0)
    content = content.strip()
    insert_data = {
        'user_id': user_id,
        "content": content,
        "last_sent": datetime.datetime.today()
    }
    if user_name:
        insert_data.update({"user_name": user_name})
    # 记录投放
    编号 = db.insert_auto_increment("river_lantern", insert_data)
    msg = f"{user_name}，河灯{编号}帮你放好了，一共收了5两银子."

    if 类型 == "回复河灯":
        回复user_id = con["user_id"]
        邮件内容 = f"您的河灯{河灯id}收到了【{user_name}】的回复！\n" \
                  f"回复内容：{你的回复}\n\n" \
                  f"原内容：{回复内容}\n\n" \
                  f"如果想要回复这个河灯可以在任意群发送“回复河灯 {编号} 你的内容”"
        await mail_client.send_mail(f"{回复user_id}@qq.com", "河灯回复通知", 邮件内容)

    # 恢复善恶
    if river_lantern <= 5:
        善恶值 = 0
        if con := db.jianghu.find_one({"_id": user_id}):
            善恶值 = con.get("善恶值", 0)
        if 善恶值 < 0:
            db.jianghu.update_one({"_id": user_id}, {"$inc": {"善恶值": 1}})
            msg += f"这是今天放的第{river_lantern+1}个河灯，善恶值+1，当前善恶值：{善恶值+1}。"
    logger.debug(f"<y>{user_id}</y> | <g>投放成功！</g> | {content}")

    return msg


async def get_river_lantern(group_id, user_id) -> Message:
    '''捡一盏三天内的河灯'''
    # 查看冷却时间
    n_cd_time = 3
    app_name = "捡河灯"
    flag, cd_time = await search_record(user_id, app_name, n_cd_time)
    if not flag:
        msg = f"[{app_name}] 冷却 > [{cd_time}]"
        return msg
    # 记录一次查询
    await search_once(user_id, app_name)
    plugins_info = db.plugins_info.find_one({"_id": group_id})
    status = True
    if plugins_info:
        status = plugins_info.get("river_lantern", {}).get("status", True)
    if not status:
        return "本群已关闭河灯功能，如果要恢复，请发送“打开 河灯”"
    _con = db.river_lantern.find({
        'last_sent': {
            "$gte": datetime.datetime.today() + datetime.timedelta(days=-3)
        }
    })
    con_list = list(_con)
    if not con_list:
        logger.debug("<r>无河灯</r>")
        return "现在找不到河灯。"

    user_con = db.user_info.find_one({"_id": user_id})
    user_lucky = 1.0
    if user_con:
        user_lucky = user_con.get("user_lucky", 1.0)
    if user_lucky >= random.uniform(0, 35):
        db.user_info.update_one({"_id": user_id},
                                {"$set": {
                                    "user_lucky": user_lucky * 0.6
                                }}, True)
        add_gold = random.randint(1, len(con_list))
        gold = 0
        _con = db.user_info.find_one({'_id': user_id})
        if _con:
            gold = _con.get("gold", 0)
        gold += add_gold
        db.user_info.update_one({"_id": user_id}, {"$set": {
            "gold": gold
        }}, True)
        msg = MessageSegment.at(user_id)
        msg += f"捡到的河灯里没有花笺，但是发现了{add_gold}两银子！"
        logger.debug(f"| <g>{user_id}</g> | 河灯银两 +{add_gold}")
        return msg

    con = random.choice(con_list)
    lantern_id = con.get("_id")
    content = con.get("content")
    user_name = con.get("user_name")
    if not content:
        logger.debug("<y>空河灯</y>")
        return "你捡到了一个空的河灯。要不你来放一个？"
    db.river_lantern.update_one({"_id": lantern_id},
                                {"$inc": {
                                    "views_num": 1
                                }})
    logger.debug(f"<g>河灯</g> | {content}")
    if isinstance(lantern_id, int):
        msg = f"花笺{lantern_id}：\n    {content}"
    else:
        msg = f"花笺：\n    {content}"
    if user_name:
        msg = f"{user_name}的" + msg
    return msg


async def my_river_lantern(user_id: int, user_name: str):
    '''查看自己的所有河灯'''
    filter = {'user_id': user_id}
    sort = list({'last_sent': -1}.items())
    limit = 10
    con = db.river_lantern.find(filter=filter, sort=sort, limit=limit)
    data = list(con)
    if not data:
        return "你还没投放过河灯。"
    datas = []
    index_num = 0
    for i in data:
        index_num += 1
        content = i["content"]
        datas.append({
            "index_num":
            index_num,
            "content":
            content,
            "is_expired": (datetime.datetime.now() - i["last_sent"]).days > 3,
            "datetime":
            i["last_sent"].strftime("%Y-%m-%d %H:%M:%S"),
            "views_num":
            i.get("views_num", 0)
        })

    logger.debug(f"<g>{user_id}</g> | 查看河灯")
    pagename = "river_lantern.html"
    img = await browser.template_to_image(user_name=user_name,
                                          user_id=user_id,
                                          pagename=pagename,
                                          datas=datas)
    return MessageSegment.image(img)
