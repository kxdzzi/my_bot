from datetime import datetime
from nonebot import export, on_regex
from nonebot.params import Depends
import re
from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters.onebot.v11.event import GroupMessageEvent
from nonebot.adapters.onebot.v11.permission import GROUP
from src.plugins.jianghu.shop import shop
from src.plugins.jianghu.auction_house import 上架商品, 下架商品, 查找商品, 购买商品, 我的商品
from src.utils.log import logger
from src.utils.scheduler import scheduler
from src.utils.config import config

from . import data_source as source

Export = export()
Export.plugin_name = "江湖"
Export.plugin_command = "江湖"
Export.plugin_usage = "江湖能容天下事，何须唯唯屈庙堂？"
Export.default_status = True

my_info = on_regex(r"^个人信息$", permission=GROUP, priority=5, block=True)
set_name = on_regex(r"^改名 [\u4e00-\u9fa5]{1,8}$", permission=GROUP, priority=5, block=True)
jianghu = on_regex(r"^江湖$", permission=GROUP, priority=5, block=True)
dig_for_treasure = on_regex(r"^挖宝( \d{1,2}){0,1}$", permission=GROUP, priority=5, block=True)
give_gold = on_regex(r"^赠送银两 *\[CQ:at,qq=\d+\] *\d+$",
                     permission=GROUP,
                     priority=5,
                     block=True)
gad_guys_ranking = on_regex(r"^恶人排行$", permission=GROUP, priority=5, block=True)
good_guys_ranking = on_regex(r"^善人排行$", permission=GROUP, priority=5, block=True)
gold_ranking = on_regex(r"^银两排行$", permission=GROUP, priority=5, block=True)
gear_ranking = on_regex(r"^神兵排行$", permission=GROUP, priority=5, block=True)
viwe_shop = on_regex(r"^商店$", permission=GROUP, priority=5, block=True)
ranking = on_regex(r"^我的背包$", permission=GROUP, priority=5, block=True)
my_gear = on_regex(r"^我的装备.*$", permission=GROUP, priority=5, block=True)
check_gear = on_regex(r"^查看装备 .+$", permission=GROUP, priority=5, block=True)
tag_gear = on_regex(r"^标记装备 .+$", permission=GROUP, priority=5, block=True)
use_gear = on_regex(r"^装备 .+$", permission=GROUP, priority=5, block=True)
purchase_goods = on_regex(r"^购买 .+$", permission=GROUP, priority=5, block=True)
use_goods = on_regex(r"^使用 .+$", permission=GROUP, priority=5, block=True)
give = on_regex(r"^赠送 *\[CQ:at,qq=\d+\] *.+$",
                permission=GROUP,
                priority=5,
                block=True)
practice_qihai = on_regex(r"^修炼气海 \d+$", permission=GROUP, priority=5, block=True)
recovery_qihai = on_regex(r"^恢复气海 \d+$", permission=GROUP, priority=5, block=True)
comprehension_skill = on_regex(r"^领悟武学$",
                               permission=GROUP,
                               priority=5,
                               block=True)
view_skill = on_regex(r"^查看武学 .{2,5}$", permission=GROUP, priority=5, block=True)
set_skill = on_regex(r"^配置武学 .+ *\d{0,1}$", permission=GROUP, priority=5, block=True)
view_skill_set = on_regex(r"^查看武学配置$", permission=GROUP, priority=5, block=True)
save_skill = on_regex(r"^保存武学配置 .+$", permission=GROUP, priority=5, block=True)
del_skill = on_regex(r"^删除武学配置 .+$", permission=GROUP, priority=5, block=True)
forgotten_skill = on_regex(r"^遗忘武学 .+$", permission=GROUP, priority=5, block=True)

impart_skill = on_regex(r"^传授武学 *\[CQ:at,qq=\d+\] *(.+?)$",
                        permission=GROUP,
                        priority=5,
                        block=True)

pk = on_regex(r"^(切磋|偷袭|死斗) *(\[CQ:at,qq=\d+\]|.{1,8}) *$",
              permission=GROUP,
              priority=5,
              block=True)
pk_log = on_regex(r"^战斗记录 *\d+(.\d+){0,1}$", permission=GROUP, priority=5, block=True)

compose = on_regex(r"^合成(材料|图纸).*?$", permission=GROUP, priority=5, block=True)

build_equipment = on_regex(r"^打造装备 .+? .+?$",
                           permission=GROUP,
                           priority=5,
                           block=True)
inlay_equipment = on_regex(r"^镶嵌装备 .+? .+?$",
                           permission=GROUP,
                           priority=5,
                           block=True)
discard_equipment = on_regex(r"^丢弃装备 .+?$",
                             permission=GROUP,
                             priority=5,
                             block=True)
rebuild_equipment = on_regex(r"^重铸装备 .+?$",
                             permission=GROUP,
                             priority=5,
                             block=True)
remove_equipment = on_regex(r"^摧毁装备 .+?$",
                            permission=GROUP,
                            priority=5,
                            block=True)

sell_equipment = on_regex(r"^出售装备 .+?$",
                          permission=GROUP,
                          priority=5,
                          block=True)

world_boss = on_regex(r"^世界首领( .{2}){0,1}$", permission=GROUP, priority=5, block=True)
claim_rewards = on_regex(r"^领取首领奖励$", permission=GROUP, priority=5, block=True)

healing = on_regex(r"^疗伤$", permission=GROUP, priority=5, block=True)

healing = on_regex(r"^疗伤$", permission=GROUP, priority=5, block=True)

put_on_shelves = on_regex(r"^上架(商品|物品) .+$",
                          permission=GROUP,
                          priority=5,
                          block=True)

pull_off_shelves = on_regex(r"^下架(商品|物品) \d+$",
                            permission=GROUP,
                            priority=5,
                            block=True)

find_commodity = on_regex(r"^(交易行|查找(商品|物品)).*$",
                          permission=GROUP,
                          priority=5,
                          block=True)

buy_commodity = on_regex(r"^购买(商品|物品) \d+$",
                         permission=GROUP,
                         priority=5,
                         block=True)

my_commodity = on_regex(r"^我的(商品|物品)\d*$",
                        permission=GROUP,
                        priority=5,
                        block=True)

start_dungeon = on_regex(r"^(秘境|秘境首领) .+$",
                         permission=GROUP,
                         priority=5,
                         block=True)
view_dungeon = on_regex(r"^查看秘境 .+$", permission=GROUP, priority=5, block=True)
dungeon_progress = on_regex(r"^秘境进度$",
                            permission=GROUP,
                            priority=5,
                            block=True)

bind_email = on_regex(r"^绑定邮箱 .+$", permission=GROUP, priority=5, block=True)
make_sure_bind_email = on_regex(r"^确认绑定 .+ \d{6}$", permission=GROUP, priority=5, block=True)


def get_content(event: GroupMessageEvent) -> str:
    '''从前置这些可前可后的消息中获取name'''
    text = event.get_plaintext()
    text_list = text.split()
    return text_list[1:]


@bind_email.handle()
async def _(event: GroupMessageEvent, res=Depends(get_content)):
    msg = await source.bind_email(res)
    await bind_email.finish(msg)


@make_sure_bind_email.handle()
async def _(event: GroupMessageEvent, res=Depends(get_content)):
    user_id = event.user_id
    msg = await source.make_sure_bind_email(user_id, res)
    await make_sure_bind_email.finish(msg)


@my_info.handle()
async def _(event: GroupMessageEvent):
    '''个人信息'''
    user_id = event.user_id
    group_id = event.group_id
    user_name = event.sender.nickname
    logger.info(f"<y>群{group_id}</y> | <g>{user_id}</g> | 查看个人信息")
    msg = await source.get_my_info(user_id, user_name)
    await my_info.finish(msg)


@set_name.handle()
async def _(event: GroupMessageEvent, res=Depends(get_content)):
    '''改名'''
    user_id = event.user_id
    group_id = event.group_id
    logger.info(f"<y>群{group_id}</y> | <g>{user_id}</g> | 查看个人信息")
    msg = await source.set_name(user_id, res)
    await set_name.finish(msg)


@practice_qihai.handle()
async def _(event: GroupMessageEvent, res=Depends(get_content)):
    '''修炼气海'''
    user_id = event.user_id
    msg = await source.practice_qihai(user_id, res)
    await practice_qihai.finish(msg)


@recovery_qihai.handle()
async def _(event: GroupMessageEvent, res=Depends(get_content)):
    '''恢复气海'''
    user_id = event.user_id
    msg = await source.recovery_qihai(user_id, res)
    await recovery_qihai.finish(msg)


@dig_for_treasure.handle()
async def _(event: GroupMessageEvent, res=Depends(get_content)):
    '''挖宝'''
    user_id = event.user_id
    group_id = event.group_id
    number = 1
    if len(res) == 1:
        number = int(res[0])
    logger.info(f"<y>群{group_id}</y> | <g>{user_id}</g> | 挖宝")
    msg = await source.dig_for_treasure(user_id, number)
    await dig_for_treasure.finish(msg)


@put_on_shelves.handle()
async def _(event: GroupMessageEvent, res=Depends(get_content)):
    '''上架物品'''
    user_id = event.user_id
    if user_id == 80000000:
        await put_on_shelves.finish("这条路是孤独的，只能前行，退无可退。")
    group_id = event.group_id
    logger.info(f"<y>群{group_id}</y> | <g>{user_id}</g> | 上架物品")
    msg = await 上架商品(user_id, *res)
    await put_on_shelves.finish(msg)


@pull_off_shelves.handle()
async def _(event: GroupMessageEvent, res=Depends(get_content)):
    '''下架物品'''
    user_id = event.user_id
    if user_id == 80000000:
        await pull_off_shelves.finish("这条路是孤独的，只能前行，退无可退。")
    group_id = event.group_id
    logger.info(f"<y>群{group_id}</y> | <g>{user_id}</g> | 下架物品")
    if len(res) != 1 or not res[0].isdigit():
        await pull_off_shelves.finish("格式错误")
    编号 = int(res[0])
    msg = await 下架商品(user_id, 编号)
    await pull_off_shelves.finish(msg)


@find_commodity.handle()
async def _(event: GroupMessageEvent):
    '''查找物品'''
    user_id = event.user_id
    group_id = event.group_id
    logger.info(f"<y>群{group_id}</y> | <g>{user_id}</g> | 查找物品")
    msg = await 查找商品(event.get_plaintext())
    if not msg:
        await find_commodity.finish("找不到任何商品，有可能是的的查找姿势不对。")
    await find_commodity.finish(msg)


@my_commodity.handle()
async def _(event: GroupMessageEvent):
    '''我的商品'''
    user_id = event.user_id
    group_id = event.group_id
    logger.info(f"<y>群{group_id}</y> | <g>{user_id}</g> | 我的商品")
    msg = await 我的商品(user_id, event.get_plaintext())
    if not msg:
        await my_commodity.finish("找不到任何商品，有可能是的的查找姿势不对。")
    await my_commodity.finish(msg)


@buy_commodity.handle()
async def _(event: GroupMessageEvent, res=Depends(get_content)):
    '''购买物品'''
    user_id = event.user_id
    if user_id == 80000000:
        await buy_commodity.finish("这条路是孤独的，只能前行，退无可退。")
    group_id = event.group_id
    logger.info(f"<y>群{group_id}</y> | <g>{user_id}</g> | 购买物品")
    if len(res) != 1:
        await buy_commodity.finish("格式错误")
    msg = await 购买商品(user_id, res[0])
    await buy_commodity.finish(msg)


@jianghu.handle()
async def _(event: GroupMessageEvent):
    await my_info.finish("江湖闯荡指南: \nhttps://docs.qq.com/doc/DVlVXU09yWlJHSmlP")


@give_gold.handle()
async def _(event: GroupMessageEvent):
    """赠送银两"""
    user_id = event.user_id
    user_name = event.sender.nickname
    message = event.raw_message
    message_list = message.split()
    gold = int(message_list[-1])
    at_member_obj = re.compile(r"^赠送银两 *\[CQ:at,qq=(\d+)\] *\d+$")
    at_member_list = at_member_obj.findall(message)
    if not at_member_list:
        msg = "需要艾特"
        await give_gold.finish(msg)
    at_qq = int(at_member_list[0])
    if at_qq == user_id:
        msg = "不能给自己送银两！"
        await give_gold.finish(msg)

    msg = await source.give_gold(user_id, user_name, at_qq, gold)
    await give_gold.finish(msg)


@gad_guys_ranking.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    """恶人排行"""
    user_id = event.user_id
    msg = await source.gad_guys_ranking(bot, user_id)
    await gad_guys_ranking.finish(msg)


@good_guys_ranking.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    """善人排行"""
    user_id = event.user_id
    msg = await source.good_guys_ranking(bot, user_id)
    await good_guys_ranking.finish(msg)


@gold_ranking.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    """银两排行"""
    user_id = event.user_id
    msg = await source.gold_ranking(bot, user_id)
    await gold_ranking.finish(msg)

@gear_ranking.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    """神兵排行"""
    user_id = event.user_id
    msg = await source.gear_ranking(bot, user_id)
    await gear_ranking.finish(msg)


@viwe_shop.handle()
async def _(event: GroupMessageEvent):
    """查看商店"""
    msg = ""
    for k, v in shop.items():
        if not v.get('价格'):
            continue
        msg += f"{k} {v['价格']}\n"
    await viwe_shop.finish(msg)


@purchase_goods.handle()
async def _(event: GroupMessageEvent, res=Depends(get_content)):
    """购买物品"""
    user_id = event.user_id
    msg = await source.purchase_goods(user_id, res)
    await purchase_goods.finish(msg)


@use_goods.handle()
async def _(event: GroupMessageEvent, res=Depends(get_content)):
    """使用物品"""
    user_id = event.user_id
    msg = await source.use_goods(user_id, res)
    await use_goods.finish(msg)


@check_gear.handle()
async def _(bot: Bot, event: GroupMessageEvent, res=Depends(get_content)):
    """查看装备"""
    user_id = event.user_id
    msg = await source.check_gear(user_id, res)
    await check_gear.finish(msg)


@use_gear.handle()
async def _(event: GroupMessageEvent, res=Depends(get_content)):
    """使用装备"""
    user_id = event.user_id
    msg = await source.use_gear(user_id, res)
    await use_gear.finish(msg)


@remove_equipment.handle()
async def _(event: GroupMessageEvent, res=Depends(get_content)):
    """摧毁装备"""
    user_id = event.user_id
    if len(res) != 1:
        await remove_equipment.finish("命令格式：“摧毁装备 装备名称”")
    msg = await source.remove_equipment(user_id, res[0])
    await remove_equipment.finish(msg)


@sell_equipment.handle()
async def _(event: GroupMessageEvent, res=Depends(get_content)):
    """出售装备"""
    user_id = event.user_id
    if len(res) != 1:
        await sell_equipment.finish("命令格式：“出售装备 装备名称”")
    msg = await source.sell_equipment(user_id, res[0])
    await sell_equipment.finish(msg)


@tag_gear.handle()
async def _(event: GroupMessageEvent, res=Depends(get_content)):
    """标记装备"""
    user_id = event.user_id
    if len(res) == 2:
        装备名称, 标记 = res
    elif len(res) == 1:
        装备名称, 标记 = res[0], ""
    else:
        await tag_gear.finish("命令格式：“标记装备 装备名称 标记”或“标记装备 装备名称”")
    msg = await source.tag_gear(user_id, 装备名称, 标记)
    await tag_gear.finish(msg)


@rebuild_equipment.handle()
async def _(event: GroupMessageEvent, res=Depends(get_content)):
    """重铸装备"""
    user_id = event.user_id
    msg = "命令格式：“重铸装备 装备一 装备二”\n"\
            "其中装备一保留属性，装备二保留名称\n"\
            "或者：“重铸装备 装备 图纸1 图纸2 ...”\n"\
            "使用图纸重铸则会修改其属性，若不指定图纸则自动使用低级图纸进行重铸"
    if not re.findall("^.{2,4}[剑杖扇灯锤甲服衫袍铠链牌坠玦环]$", res[0]):
        pass
    elif len(res) == 2 and re.findall("^.{2,4}[剑杖扇灯锤甲服衫袍铠链牌坠玦环]$", res[1]):
        msg = await source.rename_equipment(user_id, res[0], res[1])
    elif len(res) > 2:
        msg = await source.rebuild_equipment(user_id, res[0], res[1:])
    elif len(res) == 1:
        msg = await source.rebuild_equipment(user_id, res[0], [])
    else:
        pass
    await rebuild_equipment.finish(msg)


@build_equipment.handle()
async def _(event: GroupMessageEvent):
    """打造装备"""
    user_id = event.user_id
    text = event.get_plaintext()
    msg = await source.build_equipment(user_id, text)
    await build_equipment.finish(msg)


@inlay_equipment.handle()
async def _(event: GroupMessageEvent):
    """镶嵌装备"""
    user_id = event.user_id
    text = event.get_plaintext()
    msg = await source.inlay_equipment(user_id, text)
    await inlay_equipment.finish(msg)


@discard_equipment.handle()
async def _(event: GroupMessageEvent):
    """丢弃装备"""
    user_id = event.user_id
    text = event.get_plaintext()
    msg = await source.discard_equipment(user_id, text)
    await discard_equipment.finish(msg)


@compose.handle()
async def _(event: GroupMessageEvent):
    """合成物品"""
    text = event.get_plaintext()
    res = text.split()
    user_id = event.user_id
    msg = await source.compose(user_id, res)
    await compose.finish(msg)


@ranking.handle()
async def _(event: GroupMessageEvent):
    """打开背包"""
    user_id = event.user_id
    msg = await source.ranking(user_id)
    await ranking.finish(msg)


@my_gear.handle()
async def _(event: GroupMessageEvent):
    """查看装备"""
    user_id = event.user_id
    text = event.get_plaintext()
    re_obj = re.compile(r"(\d+)")
    d_list = re_obj.findall(text)
    n = 1
    if d_list:
        n = int(d_list[0])
    elif text_list := text.split():
        text_list_len = len(text_list)
        if text_list_len == 2:
            if len(text_list[1]) != 2:
                await my_gear.finish("格式错误")
            n = text_list[1]
    msg = await source.my_gear(user_id, n)
    await my_gear.finish(msg)


@comprehension_skill.handle()
async def _(event: GroupMessageEvent):
    """领悟武学"""
    user_id = event.user_id
    msg = await source.comprehension_skill(user_id)
    await comprehension_skill.finish(msg)

@forgotten_skill.handle()
async def _(event: GroupMessageEvent, res=Depends(get_content)):
    """遗忘武学"""
    user_id = event.user_id
    msg = await source.forgotten_skill(user_id, res)
    await forgotten_skill.finish(msg)


@set_skill.handle()
async def _(event: GroupMessageEvent, res=Depends(get_content)):
    """配置武学"""
    user_id = event.user_id
    msg = await source.set_skill(user_id, res)
    await set_skill.finish(msg)


@view_skill.handle()
async def _(event: GroupMessageEvent, res=Depends(get_content)):
    """查看武学"""
    msg = await source.view_skill(res)
    await view_skill.finish(msg)


@save_skill.handle()
async def _(event: GroupMessageEvent, res=Depends(get_content)):
    """保存武学配置"""
    user_id = event.user_id
    msg = await source.save_skill(user_id, res)
    await save_skill.finish(msg)


@del_skill.handle()
async def _(event: GroupMessageEvent, res=Depends(get_content)):
    """删除武学配置"""
    user_id = event.user_id
    msg = await source.del_skill(user_id, res)
    await del_skill.finish(msg)


@view_skill_set.handle()
async def _(event: GroupMessageEvent):
    """查看武学配置"""
    user_id = event.user_id
    msg = await source.view_skill_set(user_id)
    await view_skill_set.finish(msg)


@world_boss.handle()
async def _(event: GroupMessageEvent, res=Depends(get_content)):
    """世界boss"""
    user_id = event.user_id
    msg = await source.pk_world_boss(user_id, res)
    await world_boss.finish(msg)


@claim_rewards.handle()
async def _(event: GroupMessageEvent):
    """领取首领奖励"""
    user_id = event.user_id
    msg = await source.claim_rewards(user_id)
    await claim_rewards.finish(msg)


@start_dungeon.handle()
async def _(event: GroupMessageEvent, res=Depends(get_content)):
    """秘境首领"""
    user_id = event.user_id
    msg = await source.start_dungeon(user_id, res)
    await start_dungeon.finish(msg)


@view_dungeon.handle()
async def _(event: GroupMessageEvent, res=Depends(get_content)):
    """秘境首领"""
    user_id = event.user_id
    msg = await source.view_dungeon(user_id, res)
    await view_dungeon.finish(msg)


@dungeon_progress.handle()
async def _(event: GroupMessageEvent):
    """秘境首领"""
    user_id = event.user_id
    msg = await source.dungeon_progress(user_id)
    await dungeon_progress.finish(msg)


@pk_log.handle()
async def _(event: GroupMessageEvent):
    """战斗记录"""
    re_obj = re.compile(r"(\d+)")
    text = event.get_plaintext()
    d_list = re_obj.findall(text)
    if len(d_list) == 2:
        日期, 编号 = d_list
    elif len(d_list) == 1:
        日期 = datetime.now().strftime("%Y%m%d")
        编号 = d_list[0]
    else:
        await pk_log.finish("输入格式错误")
    msg = await source.pk_log(日期, int(编号))
    await pk_log.finish(msg)


@impart_skill.handle()
async def _(event: GroupMessageEvent):
    '''传授武学'''
    user_id = event.user_id
    at_member_obj = re.compile(r"^传授武学 *\[CQ:at,qq=(\d*)\] *(.+?)$")
    at_member_list = at_member_obj.findall(event.raw_message)
    if not at_member_list:
        msg = "需要艾特传授目标"
        await impart_skill.finish(msg)
    at_qq = int(at_member_list[0][0])
    武学 = at_member_list[0][1]
    if at_qq == user_id:
        msg = "不可以传授给自己武学"
        await impart_skill.finish(msg)
    if at_qq < 100000:
        msg = "传授目标不正确"
        await impart_skill.finish(msg)

    msg = await source.impart_skill(user_id, at_qq, 武学)
    await impart_skill.finish(msg)


@pk.handle()
async def _(event: GroupMessageEvent):
    '''干架'''
    user_id = event.user_id
    at_member_obj = re.compile(r"^(切磋|偷袭|死斗) *[\[CQ:at,qq=]*(\d+|.{1,8})\]{0,1} *$")
    at_member_list = at_member_obj.findall(event.raw_message)
    if not at_member_list:
        msg = "需要艾特你要干的人, 或是输入正确的名字"
        await pk.finish(msg)
    动作 = at_member_list[0][0]
    目标 = at_member_list[0][1]
    msg = await source.pk(动作, user_id, 目标)
    await pk.finish(msg)


@give.handle()
async def _(event: GroupMessageEvent):
    '''送东西'''
    user_id = event.user_id
    if user_id == 80000000:
        await give.finish("这条路是孤独的，只能前行，退无可退。")
    at_member_obj = re.compile(r"^赠送 *\[CQ:at,qq=(\d*)\] *(.+?)$")
    at_member_list = at_member_obj.findall(event.raw_message)
    if not at_member_list or len(at_member_list[0]) < 2:
        msg = "赠送格式错误"
        await give.finish(msg)
    at_qq = int(at_member_list[0][0])
    物品列表 = at_member_list[0][1].split()
    if at_qq == user_id:
        msg = "不能给自己送东西"
        await give.finish(msg)

    msg = await source.give(user_id, at_qq, 物品列表)
    await give.finish(msg)


@healing.handle()
async def _(event: GroupMessageEvent):
    """疗伤"""
    user_id = event.user_id
    at_member_obj = re.compile(r"^疗伤 *\[CQ:at,qq=(\d*)\] *$")
    at_member_list = at_member_obj.findall(event.raw_message)
    target_id = user_id
    if at_member_list:
        target_id = int(at_member_list[0])
    msg = await source.healing(user_id, target_id)
    await healing.finish(msg)


@scheduler.scheduled_job("cron", hour="10,15,20,23", minute=0)
async def _():
    '''10,15,20刷新世界boss'''
    if config.node_info.get("node") == config.node_info.get("main"):
        logger.info("正在复活世界首领")
        await source.resurrection_world_boss()
        logger.info("世界首领已复活")
