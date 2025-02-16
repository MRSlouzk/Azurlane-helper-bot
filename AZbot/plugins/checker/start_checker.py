import os.path
import shutil, traceback

from nonebot.adapters.onebot.v11 import Bot
from nonebot import get_driver, get_bots
from nonebot.log import default_format

from AZbot.plugins.sync.operation import *
from AZbot.plugins.server_status.util import check
from AZbot.plugins.config import cfg
from AZbot.plugins._error import report_error
from nonebot_plugin_apscheduler import scheduler

driver = get_driver()
@driver.on_bot_connect
async def _(bot: Bot):
    if cfg["base"]["startup_notify"]:
        for user in get_driver().config.superusers:
            await bot.send_private_msg(user_id=int(user), message="Bot已启动")

    su = ()
    ccg = cfg["user"]["ccg"]
    for user in cfg["user"]["super_admin"]:
        su += (str(user), )

    if ccg != -1:
        try:
            (bot, ) = get_bots().values()
            mem_lst = await bot.call_api("get_group_member_list", group_id=ccg)
            for mem in mem_lst:
                if str(mem) in su:
                    continue
                su += (str(mem["user_id"]), )
        except:
            await report_error(traceback.format_exc(), func="start_checker")
            logger.error("无法获取ccg群成员列表, 请检查配置文件中ccg的值是否正确")

    get_driver().config.superusers = su

@driver.on_startup
async def init():

    if cfg["develop"]["debug"]:
        if os.path.exists("error.log"):
            shutil.copyfile("error.log", "error.log.bak")
            os.remove("error.log")
        logger.add("error.log", level="ERROR", format=default_format)

    proxy = cfg["base"]["network_proxy"]
    if proxy and cfg["base"]["git_proxy"] != "none":
        set_proxy(proxy)

    if not (cfg.get("user") or cfg.get("user").get("super_admin")):
        logger.error("未找到正确配置，请初始化config")
        sys.exit(0)
    elif len(cfg["user"]["super_admin"]) == 0:
        logger.error("未配置必须项 super_admin ，请配置完成后重新启动")
        sys.exit(0)

    if cfg["base"]["startup_update"]:
        local_file_check()
        if sync_repo():
            logger.info("数据更新成功")
    else:
        logger.info("config.yaml中\"startup_update\"选项已关闭, 将不会更新数据")
        if not os.path.exists("data"):
            logger.warning("data文件夹不存在，使用时会报错，请将\"startup_update\"选项打开后重新启动")
            sys.exit(0)

    # 需要读取文件无法直接预加载
    auto_check = cfg["func"]["server_status_monitor_refresh_time"]
    if (not isinstance(auto_check, int)):
        pass
    else:
        if auto_check < 30 or auto_check > 6000:
            logger.info(f"server_status_monitor_refresh_time{auto_check}, 正常范围为1~1440, 定时检查将不会生效")
        else:
            scheduler.add_job(check, "interval", seconds=auto_check)