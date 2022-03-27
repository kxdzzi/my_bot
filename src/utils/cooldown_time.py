from src.utils.db import db
import time


async def search_record(search_id: int, app_name: str, cd_time: int):
    '''是否能够查询'''
    _con = db.search_record.find_one({'_id': search_id})
    if not _con:
        time_last = 0
    else:
        time_last = _con.get(app_name, 0)
    time_now = int(time.time())
    over_time = over_time = time_now - time_last
    if over_time > cd_time:
        return True, 0
    left_cd = cd_time - over_time
    if left_cd >= 3600:
        time_fmt = "%H:%M:%S"
    elif left_cd >= 60:
        time_fmt = "%M分%S秒"
    else:
        time_fmt = "%S秒"
    return False, time.strftime(time_fmt, time.gmtime(left_cd))


async def search_once(search_id: int, app_name: str):
    '''查询app一次'''
    db.search_record.update_one({'_id': search_id},
                                {'$set': {
                                    app_name: int(time.time())
                                }}, True)
