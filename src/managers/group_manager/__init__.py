import datetime
from typing import Literal

from nonebot import get_bots, on_notice, on_regex, on_request
from nonebot.adapters.onebot.v11 import Bot, Event, MessageSegment
from nonebot.adapters.onebot.v11.event import (FriendRequestEvent,
                                               GroupDecreaseNoticeEvent,
                                               GroupIncreaseNoticeEvent,
                                               GroupMessageEvent,
                                               GroupRequestEvent,
                                               PrivateMessageEvent)
from nonebot.adapters.onebot.v11.permission import (GROUP, GROUP_ADMIN,
                                                    GROUP_OWNER)
from nonebot.message import event_postprocessor
from nonebot.params import Depends
from nonebot.permission import SUPERUSER
from nonebot.rule import Rule
from src.utils.black_list import check_black_list
from src.utils.browser import browser
from src.utils.config import config
from src.utils.db import db
from src.utils.log import logger

from . import data_source as source

'''
群管理插件，实现功能有：
* 绑定服务器
* 设置活跃值
* 机器人开关
* 进群通知，离群通知
* 菜单
* 管理员帮助
* 滴滴
'''

bind_server = on_regex(pattern=r"^绑定 [\u4e00-\u9fa5]+$",
                       permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER,
                       priority=2,
                       block=True)  # 绑定服务器

set_activity = on_regex(pattern=r"^活跃值 (\d){1,2}$",
                        permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER,
                        priority=2,
                        block=True)  # 设置活跃值[0-99]

robot_status = on_regex(pattern=r"^(说话|闭嘴)$",
                        permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER,
                        priority=7,
                        block=True)  # 设置机器人开关

notice = on_regex(pattern=r"^((离群)|(进群))通知 ",
                  permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER,
                  priority=2,
                  block=True)  # 离群通知，进群通知

meau = on_regex(pattern=r"^((菜单)|(状态))$",
                permission=GROUP,
                priority=3,
                block=True)  # 菜单

instructions_for_use = on_regex(pattern=r"^使用说明$",
                                permission=GROUP,
                                priority=3,
                                block=True)  # 菜单

exit_group = on_regex(pattern=r"^(退群 \d+)$",
                      permission=SUPERUSER,
                      priority=1,
                      block=True)

bot_list = on_regex(pattern=r"^机器人列表$",
                    permission=GROUP,
                    priority=5,
                    block=True)

check_repeat_bot = on_regex(pattern=r"(冷却)",
                            permission=GROUP,
                            priority=10,
                            block=True)


async def _is_someone_in_group(bot: Bot, event: Event) -> bool:
    return isinstance(event, GroupIncreaseNoticeEvent)


someone_in_group = on_notice(rule=Rule(_is_someone_in_group),
                             priority=3,
                             block=True)


async def _is_group_decrease_notice(bot: Bot, event: Event) -> bool:
    return isinstance(event, GroupDecreaseNoticeEvent)


group_decrease_notice = on_notice(rule=Rule(_is_group_decrease_notice),
                                  priority=3,
                                  block=True)

group_request = on_request(priority=3, block=True)

friend_request = on_request(priority=3, block=True)

manage_group = config.bot_conf.get("manage_group", [])

archive = db.client["archive"]


@event_postprocessor
async def _(bot: Bot, event: GroupMessageEvent) -> None:
    """
    群消息总入口
    """
    group_id = event.group_id
    if group_id in manage_group:
        return
    group_info = await bot.get_group_info(group_id=group_id)
    group_name = group_info["group_name"]
    bot_id = int(bot.self_id)
    user_id = event.user_id
    nickname = event.sender.nickname
    role = event.sender.role
    message = event.raw_message
    sent_time = datetime.datetime.now()
    chat_log = archive[sent_time.strftime("chat-log-%Y-%m-%d")]
    chat_log.insert_one({
        "bot_id": bot_id,
        "role": role,
        "group_id": group_id,
        "group_name": group_name,
        "user_id": user_id,
        "nickname": nickname,
        "sent_time": sent_time,
        "message": message
    })
    # 记录群最后发言时间
    db.group_conf.update_one({
        "_id": group_id,
    }, {"$set": {
        "bot_id": bot_id,
        "last_sent": sent_time
    }}, True)
    if len(message) >= 10:
        if await source.tianjianhongfu(bot, group_id, user_id, nickname):
            return
        await source.play_picture(bot, event, group_id)


# -------------------------------------------------------------
#   Depends依赖
# -------------------------------------------------------------
def get_name(event: GroupMessageEvent) -> str:
    '''获取后置文本内容'''
    return event.get_plaintext().split(" ")[-1]


def get_private_message(event: PrivateMessageEvent) -> str:
    '''获取私聊后置内容'''
    return event.get_plaintext().split(" ")[-1]


def get_status(event: GroupMessageEvent) -> bool:
    '''获取机器人开关'''
    status = event.get_plaintext()
    return status == "说话"


def get_notice_type(event: GroupMessageEvent) -> Literal["离群通知", "进群通知"]:
    '''返回通知类型'''
    return event.get_plaintext()[:4]

# ----------------------------------------------------------------
#  matcher实现
# ----------------------------------------------------------------


@bind_server.handle()
async def _(event: GroupMessageEvent, name: str = Depends(get_name)):
    '''绑定服务器'''
    server = await source.get_main_server(name)
    if server is None:
        await bind_server.finish(f"绑定失败，未找到服务器：{name}")

    await source.bind_server(event.group_id, server)
    await bind_server.finish(f"绑定服务器【{server}】成功！")


@set_activity.handle()
async def _(event: GroupMessageEvent, name: str = Depends(get_name)):
    '''设置活跃值'''
    activity = int(name)
    await source.set_activity(event.group_id, activity)
    await set_activity.finish(f"机器人当前活跃值为：{name}")


@robot_status.handle()
async def _(event: GroupMessageEvent, status: bool = Depends(get_status)):
    '''设置机器人开关'''
    await source.set_status(event.group_id, status)
    name = "开启" if status else "关闭"
    await robot_status.finish(f"设置成功，机器人当前状态为：{name}")


@meau.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    '''菜单'''
    pagename = "meau.html"
    meau_data = await source.get_meau_data(event.group_id)
    nickname = db.bot_info.find_one({
        "_id": int(bot.self_id)
    }).get("bot_name", "二猫子")
    bot_id = bot.self_id

    img = await browser.template_to_image(pagename=pagename,
                                          data=meau_data,
                                          nickname=nickname,
                                          bot_id=bot_id)
    await meau.finish(MessageSegment.image(img))


@instructions_for_use.handle()
async def _():
    '''使用说明'''
    msg = "https://docs.qq.com/doc/DVkNsaGVzVURMZ0ls"
    await instructions_for_use.finish(msg)


@friend_request.handle()
async def _(bot: Bot, event: FriendRequestEvent):
    """加好友事件"""
    bot_id = int(bot.self_id)
    user_id = int(event.user_id)
    bot_info = db.bot_info.find_one({"_id": bot_id})
    logger.info(f"<y>bot({bot_id})</y> | <y>加好友({user_id})</y>")
    if bot_info.get("master"):
        approve = True
    else:
        is_black, _ = check_black_list(user_id, "QQ")
        approve = not is_black and bot_info.get("work_stat")
    await bot.set_friend_add_request(
        flag=event.flag,
        approve=approve,
    )


@group_request.handle()
async def _(bot: Bot, event: GroupRequestEvent):
    """加群事件响应"""
    bot_id = int(bot.self_id)
    user_id = int(event.user_id)
    group_id = event.group_id

    approve, reason = await source.check_add_bot_to_group(
        bot, user_id, group_id)

    if not approve:
        logger.info(
            f"<y>bot({bot_id})</y> | <r>拒绝加群群({group_id})</r> | {reason}")
    try:
        await bot.set_group_add_request(flag=event.flag,
                                        sub_type=event.sub_type,
                                        approve=approve,
                                        reason=reason)
    except:
        pass


@notice.handle()
async def _(event: GroupMessageEvent,
            notice_type: Literal["离群通知", "进群通知"] = Depends(get_notice_type)):
    '''设置通知内容'''
    result = await source.handle_data_notice(event.group_id, notice_type,
                                             event.raw_message)
    if not result:
        await notice.finish("好家伙，违规词不要乱设置！！")
    await notice.finish(f"设置{notice_type}成功！")


@bot_list.handle()
async def _(event: GroupMessageEvent):
    '''查看机器人列表'''
    bot_info_list = db.bot_info.find({"work_stat": True})
    available_bot_list = []
    for bot_info in bot_info_list:
        bot_id = int(bot_info.get("_id"))
        db_bot_info = db.bot_info.find_one({'_id': bot_id})
        access_group_num = db_bot_info.get("access_group_num", 50)
        bot_group_num = db.group_conf.count_documents({"bot_id": bot_id})
        on_line = db_bot_info.get("online_status", False)
        if on_line and (bot_group_num < access_group_num):
            available_bot_list.append(
                f"{bot_id: 11d} | {bot_group_num}/{access_group_num}"
            )
    if available_bot_list:
        msg = "  机器人QQ   | 群数量\n"
        msg += "\n".join(available_bot_list) 
    else:
        msg = "暂无可用的机器人"
    await bot_list.finish(msg)


@someone_in_group.handle()
async def _(bot: Bot, event: GroupIncreaseNoticeEvent):
    '''
    群成员增加事件
    '''
    group_id = event.group_id
    user_id = event.user_id
    self_id = event.self_id
    # 判断是否是机器人进群
    if user_id == self_id:
        # 若群id不在管理群列表, 则需要进行加群条件过滤
        if group_id not in manage_group:
            # 判断是否有其他机器人
            _con = db.bot_info.find()
            if _con:
                bot_id_list = [int(i["_id"]) for i in _con]
            group_member_list = await bot.get_group_member_list(
                group_id=group_id)
            for usr in group_member_list:
                group_user_id = int(usr["user_id"])
                if group_user_id in bot_id_list and group_user_id != self_id:
                    msg = "一群不容二我！！你说"
                    msg += MessageSegment.at(group_user_id)
                    msg += "是什么情况？我退了！！\n你在把它踢了之前，不要再拉我了！"
                    logger.warning(
                        f"<y>bot({self_id})</y> | <r>重复加群({group_id})</r>")
                    await source.del_bot_to_group(bot, group_id, msg)
                    await someone_in_group.finish()
        logger.info(f"<y>bot({self_id})</y> | <g>加群({group_id})</g>")
        # 注册群
        await source.add_bot_to_group(group_id, int(self_id))
        msg = '老子来了，发送“菜单”看看吧！'
        await someone_in_group.finish(msg)

    flag = await source.get_notice_status(group_id, "welcome_status")
    logger.info(f"<y>成员({user_id})</y> | <g>加群({group_id})</g>")
    if flag:
        msg = await source.message_decoder(bot, event, "进群通知")
        if msg:
            await someone_in_group.finish(msg)


@group_decrease_notice.handle()
async def _(bot: Bot, event: GroupDecreaseNoticeEvent):
    """成员退群"""
    group_id = event.group_id
    user_id = event.user_id
    self_id = event.self_id
    _con = db.bot_info.find()
    if _con:
        bot_id_list = [int(i["_id"]) for i in _con]
    # 在机器人列表中且非自己
    if user_id in bot_id_list and user_id != self_id:
        msg = "哈哈哈，你走了正好，群里就只剩下我一个了！哈哈哈哈哈哈哈！"
        await notice.finish(msg)
    # 判断是否是机器人退群
    if user_id == self_id:
        # 删除群中的bot_id
        await source.del_bot_to_group(bot, group_id, exit_group=False)
        logger.info(f"<y>bot({self_id})</y> | <r>退群({group_id})</r>")
        await notice.finish()
    # 有人退群，发送退群消息
    flag = await source.get_notice_status(group_id, "someoneleft_status")
    logger.info(f"<y>成员({user_id})</y> | <r>退群({group_id})</r>")
    if flag:
        msg = await source.message_decoder(bot, event, "离群通知")
        if msg:
            await notice.finish(msg)


@check_repeat_bot.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    '''发言检测，重复机器人则退群'''
    group_id = event.group_id
    user_id = event.user_id
    self_id = event.self_id
    # 管理群无视该情况
    if group_id in manage_group:
        return
    # 机器人列表
    _con = db.bot_info.find()
    if _con:
        bot_id_list = [int(i["_id"]) for i in _con]
    if user_id in bot_id_list:
        # 删除群中的bot_id
        msg = MessageSegment.at(user_id)
        msg += "居然也在群里？我还以为我是唯一，没想到我什么都不是！\n我走了，你别来烦我！"
        logger.warning(f"<y>bot({self_id})</y> | <r>检测到重复加群({group_id})</r>")
        await source.del_bot_to_group(bot, group_id, msg)
    await check_repeat_bot.finish()


@exit_group.handle()
async def _(bot: Bot,
            event: PrivateMessageEvent,
            cmd_arg: str = Depends(get_private_message)):
    '''退群指令'''
    group_id = int(cmd_arg)
    bot_id = int(bot.self_id)
    msg = "我老大喊我回去吃饭了，不过我觉得可能没那么简单。你们还是问问我老大是啥情况吧！各位再会！"
    ret_msg = await source.del_bot_to_group(bot, group_id, msg)
    logger.info(
        f"<y>bot({bot_id})</y> | <r>指令退群({group_id})</r> | <g>管理员({event.user_id})</g>"
    )
    await exit_group.finish(ret_msg)
