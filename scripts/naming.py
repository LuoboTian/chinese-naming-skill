#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
 中文取名本地计算脚本
八字排盘 + 五行分析 + 紫微十二宫 + 三才五格 + 生肖喜忌 + 卦象 + 音韵 + 字义寓意
零第三方依赖，仅标准库。

本项目自主组织计算、候选生成和解释流程，使用仓库内的参考数据完成本地分析。
"""
import sys
import os
import json
import argparse
import re
from datetime import datetime, date, timedelta
from pathlib import Path

# ---------------- 基础数据 ----------------

GAN = "甲乙丙丁戊己庚辛壬癸"
ZHI = "子丑寅卯辰巳午未申酉戌亥"
WUXING_GAN = {"甲":"木","乙":"木","丙":"火","丁":"火","戊":"土","己":"土","庚":"金","辛":"金","壬":"水","癸":"水"}
WUXING_ZHI = {"子":"水","丑":"土","寅":"木","卯":"木","辰":"土","巳":"火","午":"火","未":"土","申":"金","酉":"金","戌":"土","亥":"水"}
# 藏干（用于取用神时参考）
CANG_GAN = {
    "子":["癸"],"丑":["己","癸","辛"],"寅":["甲","丙","戊"],"卯":["乙"],
    "辰":["戊","乙","癸"],"巳":["丙","庚","戊"],"午":["丁","己"],"未":["己","丁","乙"],
    "申":["庚","壬","戊"],"酉":["辛"],"戌":["戊","辛","丁"],"亥":["壬","甲"]
}
# 十二长生（简化：仅用于日主强弱判断辅助）
SHENG = "长生沐浴冠带临官帝旺衰病死墓绝胎养"
# 三才五格吉凶（81数理吉凶速查：吉/半吉/凶）
SHU_LI = {
    1:"吉",2:"凶",3:"吉",4:"凶",5:"吉",6:"吉",7:"吉",8:"吉",9:"凶",10:"凶",
    11:"吉",12:"凶",13:"吉",14:"凶",15:"吉",16:"吉",17:"吉",18:"吉",19:"凶",20:"凶",
    21:"吉",22:"凶",23:"吉",24:"吉",25:"吉",26:"凶",27:"凶",28:"凶",29:"吉",30:"半吉",
    31:"吉",32:"吉",33:"吉",34:"凶",35:"吉",36:"半吉",37:"吉",38:"半吉",39:"吉",40:"凶",
    41:"吉",42:"凶",43:"凶",44:"凶",45:"吉",46:"凶",47:"吉",48:"吉",49:"凶",50:"半吉",
    51:"半吉",52:"吉",53:"凶",54:"凶",55:"半吉",56:"凶",57:"吉",58:"半吉",59:"凶",60:"凶",
    61:"吉",62:"凶",63:"吉",64:"凶",65:"吉",66:"凶",67:"吉",68:"吉",69:"凶",70:"凶",
    71:"半吉",72:"凶",73:"半吉",74:"凶",75:"半吉",76:"凶",77:"半吉",78:"半吉",79:"凶",80:"凶",
    81:"吉"
}
# 生肖
SHENGXIAO = ["鼠","牛","虎","兔","龙","蛇","马","羊","猴","鸡","狗","猪"]
# 生肖宜用字根
SX_GOOD = {
    "鼠":["氵","水","木","禾","王","口","宀"],
    "牛":["艹","氵","宀","禾","豆","米","辶"],
    "虎":["山","王","氵","木","宀","月"],
    "兔":["艹","禾","木","宀","口","氵"],
    "龙":["氵","王","月","日","雨","申"],
    "蛇":["艹","宀","口","木","禾"],
    "马":["艹","木","禾","宀","王","氵"],
    "羊":["艹","禾","木","宀","口","氵"],
    "猴":["木","氵","宀","王","禾"],
    "鸡":["禾","豆","米","宀","氵","艹"],
    "狗":["氵","宀","王","月","禾"],
    "猪":["氵","艹","木","宀","王","禾"]
}
# 声调（普通话）
def get_tone(ch):
    """返回 1-4 或 0，优先加载 references/tones.md 全量声调表。"""
    if ch in TONE_EXT:
        return TONE_EXT[ch]
    if '\u4e00' <= ch <= '\u9fff':
        return _TONE_MAP.get(ch, 0)
    return 0

TONE_EXT = {}

def load_tones():
    """加载 references/tones.md 全量声调表（字 声调）。"""
    global TONE_EXT
    here = os.path.dirname(os.path.abspath(__file__))
    ref = os.path.join(os.path.dirname(here), "references", "tones.md")
    if os.path.exists(ref):
        with open(ref, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) >= 2 and len(parts[0]) == 1:
                    try:
                        TONE_EXT[parts[0]] = int(parts[1])
                    except ValueError:
                        pass

# 常用字声调表（精选起名高频字，完整版可扩展）
_TONE_MAP = {}
_TONE_TABLE = {
    "一":1,"二":4,"三":1,"四":4,"五":3,"六":4,"七":1,"八":1,"九":3,"十":2,
    "天":1,"地":4,"人":2,"大":4,"小":3,"中":1,"山":1,"水":3,"风":1,"云":2,
    "日":4,"月":4,"星":1,"光":1,"明":2,"文":2,"武":3,"英":1,"雄":2,"杰":2,
    "子":3,"安":1,"宁":2,"平":2,"和":2,"乐":4,"福":2,"禄":4,"寿":4,"喜":3,
    "嘉":1,"祥":2,"瑞":4,"祺":2,"欣":1,"悦":4,"怡":2,"然":2,"雅":3,"韵":4,
    "诗":1,"书":1,"画":4,"琴":2,"棋":2,"梅":2,"兰":2,"竹":2,"菊":2,
    "松":1,"柏":3,"桂":4,"楠":2,"桐":2,"枫":1,"林":2,"森":1,"源":2,"泉":2,
    "海":3,"涛":1,"波":1,"澜":2,"溪":1,"浩":4,"瀚":4,"泽":2,"润":4,"清":1,
    "冰":1,"雪":3,"霜":1,"露":4,"雨":3,"雷":2,"霆":2,"震":4,"虹":2,"霞":2,
    "玉":4,"金":1,"银":2,"宝":3,"珠":1,"琳":2,"瑶":2,"瑾":3,"瑜":2,"琪":2,
    "瑞":4,"珊":1,"瑚":2,"琦":2,"琬":3,"玮":3,"珩":2,"玟":2,"玥":4,"珺":4,
    "浩":4,"然":2,"宇":3,"宙":4,"宏":2,"远":3,"达":2,"飞":1,"腾":2,"翔":2,
    "鹏":2,"鹤":4,"凤":4,"龙":2,"麒麟":2,"虎":3,"豹":4,"骏":4,"骥":4,
    "志":4,"毅":4,"勇":3,"强":2,"刚":1,"健":4,"康":1,"泰":4,"盛":4,"昌":1,
    "国":2,"家":1,"华":2,"夏":4,"春":1,"秋":1,"冬":1,"思":1,"念":4,"恩":1,
    "德":2,"仁":2,"义":4,"礼":3,"智":4,"信":4,"诚":2,"忠":1,"孝":4,"谦":1,
    "勤":2,"俭":3,"善":4,"美":3,"丽":4,"婉":3,"娴":2,"淑":1,"慧":4,"敏":3,
    "捷":2,"颖":3,"秀":4,"娟":1,"婷":2,"娇":1,"娜":4,"妍":2,"嫣":1,"芙":2,
    "蓉":2,"薇":1,"萱":1,"芷":3,"若":4,"芸":2,"芹":2,"青":1,"蓝":2,"碧":4,
    "翠":4,"丹":1,"彤":2,"红":2,"紫":3,"黛":4,"蓝":2,"雪":3,"雯":2,"霭":3,
    "曦":1,"晟":4,"昊":4,"昱":4,"煜":4,"炜":3,"烨":4,"烁":4,"灿":4,"焕":4,
    "旭":4,"昂":2,"昶":3,"晏":4,"晴":2,"暄":1,"暖":3,"曜":4,"恒":2,"屹":4,
    "峥":1,"嵘":2,"巍":1,"岩":2,"岳":4,"峰":1,"岭":3,"川":1,"河":2,"江":1,
    "湖":2,"泊":2,"沐":4,"沛":4,"沁":4,"洺":2,"潇":1,"漪":1,"淳":2,"涵":2,
    "淇":2,"淑":1,"添":1,"淼":3,"渊":1,"渝":2,"澄":2,"澈":4,"澜":2,"瀚":4,
    "灵":2,"程":2,"锦":3,"铭":2,"锋":1,"钧":1,"铁":3,"锟":1,"钢":1,"锐":4,
    "鉴":4,"鑫":1,"铄":4,"钦":1,"铭":2,"键":4,"镇":4,"锦":3,"铮":1,"铜":2,
    "柏":3,"柳":3,"桃":2,"梨":2,"杏":4,"梅":2,"楠":2,"槿":3,"槐":2,"樾":4,
    "枘":4,"桁":2,"栩":3,"楷":3,"楟":2,"楼":2,"乐":4,"枢":1,"棋":2,"森":1,
    "楚":3,"梦":4,"桐":2,"梓":3,"棠":2,"榆":2,"榕":2,"槿":3,"檀":2,"欣":1,
}
for _k, _v in _TONE_TABLE.items():
    _TONE_MAP[_k] = _v

# 农历数据表（1900-2100，标准 lunarInfo）
LUNAR_INFO = [
0x04bd8,0x04ae0,0x0a570,0x054d5,0x0d260,0x0d950,0x16554,0x056a0,0x09ad0,0x055d2,
0x04ae0,0x0a5b6,0x0a4d0,0x0d250,0x1d255,0x0b540,0x0d6a0,0x0ada2,0x095b0,0x14977,
0x04970,0x0a4b0,0x0b4b5,0x06a50,0x06d40,0x1ab54,0x02b60,0x09570,0x052f2,0x04970,
0x06566,0x0d4a0,0x0ea50,0x06e95,0x05ad0,0x02b60,0x186e3,0x092e0,0x1c8d7,0x0c950,
0x0d4a0,0x1d8a6,0x0b550,0x056a0,0x1a5b4,0x025d0,0x092d0,0x0d2b2,0x0a950,0x0b557,
0x06ca0,0x0b550,0x15355,0x04da0,0x0a5b0,0x14573,0x052b0,0x0a9a8,0x0e950,0x06aa0,
0x0aea6,0x0ab50,0x04b60,0x0aae4,0x0a570,0x05260,0x0f263,0x0d950,0x05b57,0x056a0,
0x096d0,0x04dd5,0x04ad0,0x0a4d0,0x0d4d4,0x0d250,0x0d558,0x0b540,0x0b5a0,0x195a6,
0x095b0,0x049b0,0x0a974,0x0a4b0,0x0b27a,0x06a50,0x06d40,0x0af46,0x0ab60,0x09570,
0x04af5,0x04970,0x064b0,0x074a3,0x0ea50,0x06b58,0x055c0,0x0ab60,0x096d5,0x092e0,
0x0c960,0x0d954,0x0d4a0,0x0da50,0x07552,0x056a0,0x0abb7,0x025d0,0x092d0,0x0cab5,
0x0a950,0x0b4a0,0x0baa4,0x0ad50,0x055d9,0x04ba0,0x0a5b0,0x15176,0x052b0,0x0a930,
0x07954,0x06aa0,0x0ad50,0x05b52,0x04b60,0x0a6e6,0x0a4e0,0x0d260,0x0ea65,0x0d530,
0x05aa0,0x076a3,0x096d0,0x04afb,0x04ad0,0x0a4d0,0x1d0b6,0x0d250,0x0d520,0x0dd45,
0x0b5a0,0x056d0,0x055b2,0x049b0,0x0a577,0x0a4b0,0x0aa50,0x1b255,0x06d20,0x0ada0,
0x14b63,0x09370,0x049f8,0x04970,0x064b0,0x168a6,0x0ea50,0x06b20,0x1a6c4,0x0aae0,
0x092e0,0x0d2e3,0x0c960,0x0d557,0x0d4a0,0x0da50,0x05d55,0x056a0,0x0a6d0,0x055d4,
0x052d0,0x0a9b8,0x0a950,0x0b4a0,0x0b6a6,0x0ad50,0x055a0,0x0aba4,0x0a5b0,0x052b0,
0x0b273,0x06930,0x07337,0x06aa0,0x0ad50,0x14b55,0x04b60,0x0a570,0x054e4,0x0d160,
0x0e968,0x0d520,0x0daa0,0x16aa6,0x056d0,0x04ae0,0x0a9d4,0x0a2d0,0x0d150,0x0f252,
0x0d520
]

LUNAR_MONTHS = ["正","二","三","四","五","六","七","八","九","十","冬","腊"]
LUNAR_DAYS = ["初一","初二","初三","初四","初五","初六","初七","初八","初九","初十",
              "十一","十二","十三","十四","十五","十六","十七","十八","十九","二十",
              "廿一","廿二","廿三","廿四","廿五","廿六","廿七","廿八","廿九","三十"]

# ---------------- 农历转换（1900-2100） ----------------

def leap_month(year):
    return LUNAR_INFO[year - 1900] & 0xf

def leap_days(year):
    if leap_month(year):
        return 30 if (LUNAR_INFO[year - 1900] & 0x10000) else 29
    return 0

def month_days(year, month):
    if LUNAR_INFO[year - 1900] & (0x10000 >> month):
        return 30
    return 29

def lunar_year_days(year):
    s = 348
    for m in range(1, 13):
        s += 1 if (LUNAR_INFO[year - 1900] & (0x10000 >> m)) else 0
    return s + leap_days(year)

def solar_to_lunar(y, m, d):
    """公历 -> 农历 (返回 农历年,月,日,是否闰月)"""
    base = date(1900, 1, 31)  # 1900-01-31 = 农历1900年正月初一
    target = date(y, m, d)
    offset = (target - base).days
    if offset < 0 or y > 2100:
        raise ValueError("仅支持1900-2100年")
    ly = 1900
    while offset >= lunar_year_days(ly):
        offset -= lunar_year_days(ly)
        ly += 1
    lm_leap = leap_month(ly)
    is_leap = False
    lm = 1
    while lm <= 12:
        md = month_days(ly, lm)
        if lm == lm_leap:
            # 先消耗正常月
            if offset < md:
                break
            offset -= md
            # 再处理闰月
            ld_leap = leap_days(ly)
            if offset < ld_leap:
                is_leap = True
                break
            offset -= ld_leap
        else:
            if offset < md:
                break
            offset -= md
        lm += 1
    return ly, lm, offset + 1, is_leap

def lunar_to_solar(ly, lm, ld, is_leap=False):
    """农历 -> 公历"""
    if not (1900 <= ly <= 2100):
        raise ValueError("仅支持1900-2100年")
    base = date(1900, 1, 31)
    offset = 0
    for y in range(1900, ly):
        offset += lunar_year_days(y)
    leap = leap_month(ly)
    for m in range(1, lm):
        offset += month_days(ly, m)
        if m == leap:
            offset += leap_days(ly)
    if is_leap and lm == leap:
        offset += month_days(ly, lm)
    offset += ld - 1
    return base + timedelta(days=offset)

# ---------------- 四柱排盘 ----------------

# 二十四节气近似日期（每月两个节，用于月柱分界；此处为简化查表，标注近似）
JIEQI_DAY = [
    (1, 6, "小寒"), (1, 20, "大寒"),
    (2, 4, "立春"), (2, 19, "雨水"),
    (3, 6, "惊蛰"), (3, 21, "春分"),
    (4, 5, "清明"), (4, 20, "谷雨"),
    (5, 6, "立夏"), (5, 21, "小满"),
    (6, 6, "芒种"), (6, 21, "夏至"),
    (7, 7, "小暑"), (7, 23, "大暑"),
    (8, 8, "立秋"), (8, 23, "处暑"),
    (9, 8, "白露"), (9, 23, "秋分"),
    (10, 8, "寒露"), (10, 24, "霜降"),
    (11, 7, "立冬"), (11, 22, "小雪"),
    (12, 7, "大雪"), (12, 22, "冬至"),
]

def jieqi_index(y, m, d):
    """返回当前日期在当年节气序列中的索引（用于月柱）。"""
    idx = (m - 1) * 2
    if d >= JIEQI_DAY[idx][1]:
        return idx
    return idx - 1

def year_ganzhi(y, m, d):
    """年柱：以立春为界。"""
    if (m, d) < (2, 4):
        y -= 1
    gan_idx = (y - 4) % 10
    zhi_idx = (y - 4) % 12
    return GAN[gan_idx] + ZHI[zhi_idx]

def month_ganzhi(y, m, d):
    """月柱：以节为界。年上起月法（天干地支同步+1）。"""
    yg = year_ganzhi(y, m, d)[0]
    yg_idx = GAN.index(yg)
    jq = jieqi_index(y, m, d)
    month_zhi_idx = (jq // 2 + 1) % 12
    mz = ZHI[month_zhi_idx]
    offset = (month_zhi_idx - 2) % 12  # 寅月=0, 卯=1, ..., 丑=11
    mg_idx = ((yg_idx % 5) * 2 + 2 + offset) % 10
    return GAN[mg_idx] + mz

# 日柱：1900-01-01 为 甲戌日（基准，经校验）
BASE_DATE = date(1900, 1, 1)
BASE_GZ = (9, 10)  # 甲戌：甲=10? no — GAN[0]=甲; 甲戌 = (0, 10)

def day_ganzhi(y, m, d):
    target = date(y, m, d)
    offset = (target - BASE_DATE).days
    gan = (0 + offset) % 10
    zhi = (10 + offset) % 12
    return GAN[gan] + ZHI[zhi]

def hour_ganzhi(day_gan, hour):
    """时柱：日上起时法（天干地支同步+1）。"""
    dg_idx = GAN.index(day_gan)
    zhi_idx = ((hour + 1) // 2) % 12
    hg_idx = ((dg_idx % 5) * 2 + zhi_idx) % 10
    return GAN[hg_idx] + ZHI[zhi_idx]

def parse_birth(value):
    """解析 YYYY-MM-DD、YYYY-MM-DD HH 或 YYYY-MM-DD HH:MM。"""
    match = re.fullmatch(
        r"(\d{4})-(\d{1,2})-(\d{1,2})"
        r"(?:\s+(\d{1,2})(?::(\d{2}))?)?", value.strip()
    )
    if not match:
        raise ValueError("日期格式应为 YYYY-MM-DD [HH[:MM]]")
    y, month, day = (int(match.group(i)) for i in range(1, 4))
    hour = int(match.group(4)) if match.group(4) is not None else 0
    minute = int(match.group(5)) if match.group(5) is not None else 0
    if hour > 23 or minute > 59:
        raise ValueError("小时应为 0-23，分钟应为 0-59")
    # datetime 负责校验月份和日期，同时避免脚本静默接受无效日期。
    datetime(y, month, day)
    return y, month, day, hour, minute, match.group(4) is not None

def build_bazi(y, m, d, hour):
    yg = year_ganzhi(y, m, d)
    mg = month_ganzhi(y, m, d)
    dg = day_ganzhi(y, m, d)
    hg = hour_ganzhi(dg[0], hour)
    return {"年柱": yg, "月柱": mg, "日柱": dg, "时柱": hg}

# ---------------- 五行统计与喜用神 ----------------

def wuxing_stats(bazi):
    stats = {"金":0, "木":0, "水":0, "火":0, "土":0}
    detail = {}
    for k, v in bazi.items():
        g, z = v[0], v[1]
        detail[k] = (WUXING_GAN[g], WUXING_ZHI[z], CANG_GAN[z])
        stats[WUXING_GAN[g]] += 1
        stats[WUXING_ZHI[z]] += 1
    return stats, detail

def xiyongshen(bazi):
    """取用神：统计五行 + 月令旺衰修正，取最弱且为日主所克/所生之平衡项。"""
    day_gan = bazi["日柱"][0]
    day_wx = WUXING_GAN[day_gan]
    stats, _ = wuxing_stats(bazi)
    # 月令旺衰修正：月支对日主的生克关系，加权计入日主强弱
    month_zhi = bazi["月柱"][1]
    month_wx = WUXING_ZHI[month_zhi]
    sheng_wo = {"木":"水","火":"木","土":"火","金":"土","水":"金"}
    # 月令得令 +1.5（生我/同我），失令 -1.5（我生/我克），平 0
    if month_wx == day_wx:
        month_factor = 1.5
    elif sheng_wo.get(day_wx) == month_wx:
        month_factor = 1.5
    else:
        month_factor = -1.5
    adjusted = stats[day_wx] + month_factor
    strong = adjusted >= 3
    weak = adjusted <= 1
    if strong:
        # 身强喜克泄耗：取日主所克（财）或所生（食伤）对应五行
        sheng = {"木":"火","火":"土","土":"金","金":"水","水":"木"}
        ke = {"木":"土","土":"水","水":"火","火":"金","金":"木"}
        candidate = [sheng[day_wx], ke[day_wx]]
        # 选八字中最弱的那个
        candidate.sort(key=lambda x: stats[x])
        return candidate[0], "身强"
    if weak:
        # 身弱喜生扶：取生我（印）或同我（比劫）
        sheng_wo2 = {"木":"水","火":"木","土":"火","金":"土","水":"金"}
        candidate = [sheng_wo2[day_wx], day_wx]
        candidate.sort(key=lambda x: stats[x])
        return candidate[0], "身弱"
    # 中和：取最缺五行
    missing = sorted(stats, key=lambda x: stats[x])[0]
    return missing, "中和"

# ---------------- 紫微十二宫（简化完整版） ----------------

ZHI_GONG = {
    0:"子",1:"丑",2:"寅",3:"卯",4:"辰",5:"巳",6:"午",7:"未",8:"申",9:"酉",10:"戌",11:"亥"
}
# 十二宫名（以命宫为起点逆时针排列）
GONG_NAMES = ["命宫","兄弟","夫妻","子女","财帛","疾厄","迁移","仆役","官禄","田宅","福德","父母"]

# 天干列表（索引0=甲）
GAN_LIST = ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"]

# 五虎遁：年干 -> 寅宫天干索引
WUHU_DUN = {0:2, 1:4, 2:6, 3:8, 4:0, 5:2, 6:4, 7:6, 8:8, 9:0}
# 验证：甲己年寅起丙(2)，乙庚年寅起戊(4)，丙辛年寅起庚(6)，丁壬年寅起壬(8)，戊癸年寅起甲(0)

# 命宫天干地支 -> 五行局表（权威表）
WUXING_JU_TAB = {
    # 宫干: {宫支分组: 局} 分组顺序：子丑/寅卯/辰巳/午未/申酉/戌亥
    "甲乙": ["金四局","水二局","火六局","金四局","水二局","火六局"],
    "丙丁": ["水二局","火六局","土五局","水二局","火六局","土五局"],
    "戊己": ["火六局","土五局","木三局","火六局","土五局","木三局"],
    "庚辛": ["土五局","木三局","金四局","土五局","木三局","金四局"],
    "壬癸": ["木三局","金四局","水二局","木三局","金四局","水二局"],
}

# 紫微星定位表（权威表）：五行局 -> 农历生日 -> 宫位索引（0=子）
ZIWEI_LOC_TAB = {
    2: {1:1,2:2,3:2,4:3,5:3,6:4,7:4,8:5,9:5,10:6,11:6,12:7,13:7,14:8,15:8,16:9,17:9,18:10,19:10,20:11,21:11,22:0,23:0,24:1,25:1,26:2,27:2,28:3,29:3,30:4},
    3: {1:4,2:1,3:2,4:5,5:2,6:3,7:6,8:3,9:4,10:7,11:4,12:5,13:8,14:5,15:6,16:9,17:6,18:7,19:10,20:7,21:8,22:11,23:8,24:9,25:0,26:9,27:10,28:1,29:10,30:11},
    4: {1:11,2:4,3:1,4:2,5:0,6:5,7:2,8:3,9:1,10:6,11:3,12:4,13:2,14:7,15:4,16:5,17:3,18:8,19:5,20:6,21:4,22:9,23:6,24:7,25:5,26:10,27:7,28:8,29:6,30:11},
    5: {1:6,2:11,3:4,4:1,5:2,6:7,7:0,8:5,9:2,10:3,11:8,12:1,13:6,14:3,15:4,16:9,17:2,18:7,19:4,20:5,21:10,22:3,23:8,24:5,25:6,26:11,27:4,28:9,29:6,30:7},
    6: {1:9,2:6,3:11,4:4,5:1,6:2,7:10,8:7,9:0,10:5,11:2,12:3,13:11,14:8,15:1,16:6,17:3,18:4,19:0,20:9,21:2,22:7,23:4,24:5,25:1,26:10,27:3,28:8,29:5,30:6},
}

# 命主星表（命宫支索引）
MING_ZHU = {0:"贪狼",1:"巨门",2:"禄存",3:"文曲",4:"廉贞",5:"武曲",6:"破军",7:"武曲",8:"廉贞",9:"文曲",10:"禄存",11:"巨门"}
# 身主星表（年支索引）
SHEN_ZHU = {0:"铃星",1:"天相",2:"天梁",3:"天同",4:"文昌",5:"天机",6:"火星",7:"天相",8:"天梁",9:"天同",10:"文昌",11:"天机"}

# 四化表（年干索引 -> (化禄, 化权, 化科, 化忌)）
SIHUA_TAB = {
    0: ("廉贞","破军","武曲","太阳"),
    1: ("天机","天梁","紫微","太阴"),
    2: ("天同","天机","文昌","廉贞"),
    3: ("太阴","天同","天机","巨门"),
    4: ("贪狼","太阴","右弼","天机"),
    5: ("武曲","贪狼","天梁","文曲"),
    6: ("太阳","武曲","太阴","天同"),
    7: ("巨门","太阳","文曲","文昌"),
    8: ("天梁","紫微","左辅","武曲"),
    9: ("破军","巨门","太阴","贪狼"),
}

def ganzhi_year(y):
    """年干支索引：(y-4) % 60 -> 天干 idx, 地支 idx。"""
    offset = (y - 4) % 60
    return offset % 10, offset % 12

def wuxing_ju(y, m, d, hour=None):
    """五行局：以命宫干支查纳音表（水二木三金四土五火六）。"""
    yg, yz = ganzhi_year(y)
    # 寅宫天干（五虎遁）
    yin_gan = WUHU_DUN[yg]
    # 命宫地支（用农历月）
    ly, lm, ld, is_leap = solar_to_lunar(y, m, d)
    hz = ((hour + 1) // 2) % 12 if hour is not None else 0
    ming_gong = (2 + (lm - 1) - hz) % 12
    # 命宫天干：从寅宫顺排到命宫地支
    ming_gan = (yin_gan + (ming_gong - 2)) % 10
    gan_pair = GAN_LIST[ming_gan // 2 * 2] + GAN_LIST[ming_gan // 2 * 2 + 1]
    # 命宫地支分组：子丑0 寅卯1 辰巳2 午未3 申酉4 戌亥5
    zhi_group = ming_gong // 2
    tab = WUXING_JU_TAB.get(gan_pair, ["土五局"]*6)
    return tab[zhi_group]

def ziwei_pan(y, m, d, hour):
    """紫微排盘：命宫/身宫/十二宫 + 十四主星 + 命主/身主 + 四化。返回 dict。"""
    hz = ((hour + 1) // 2) % 12  # 0=子时
    ly, lm, ld, is_leap = solar_to_lunar(y, m, d)
    # 命宫：寅宫起正月顺数生月，再逆数生时；身宫：顺数生时
    ming_gong = (2 + (lm - 1) - hz) % 12
    shen_gong = (2 + (lm - 1) + hz) % 12
    # 十二宫：命宫起逆时针排列
    gongs = {}
    for i, name in enumerate(GONG_NAMES):
        gongs[name] = ZHI_GONG[(ming_gong - i) % 12]
    # 五行局
    ju = wuxing_ju(y, m, d, hour)
    ju_num = {"水二局":2, "木三局":3, "金四局":4, "土五局":5, "火六局":6}[ju]
    # 紫微星定位（权威表）
    ziwei_gong = ZIWEI_LOC_TAB[ju_num].get(ld, 0)
    # 十四主星
    stars = {}
    # 紫微星系（逆时针，含空宫）：天机-1 太阳-3 武曲-4 天同-5 廉贞-8
    ziwei_offsets = {"紫微":0, "天机":1, "太阳":3, "武曲":4, "天同":5, "廉贞":8}
    for s, off in ziwei_offsets.items():
        stars[s] = ZHI_GONG[(ziwei_gong - off) % 12]
    # 天府星系：天府与紫微在寅申线对称
    tf_gong = (4 - ziwei_gong) % 12
    tianfu_offsets = {"天府":0, "太阴":1, "贪狼":2, "巨门":3, "天相":4, "天梁":5, "七杀":6}
    for s, off in tianfu_offsets.items():
        stars[s] = ZHI_GONG[(tf_gong + off) % 12]
    stars["破军"] = ZHI_GONG[(2 - ziwei_gong) % 12]
    # 命主/身主
    yg, yz = ganzhi_year(ly)
    mingzhu = MING_ZHU[ming_gong]
    shenzhu = SHEN_ZHU[yz]
    # 四化
    sihua = SIHUA_TAB.get(yg, ("","","",""))
    return {
        "农历": f"{ly}年{'闰' if is_leap else ''}{LUNAR_MONTHS[lm-1]}月{LUNAR_DAYS[ld-1]}",
        "五行局": ju,
        "命宫": gongs["命宫"],
        "身宫": ZHI_GONG[shen_gong],
        "十二宫": gongs,
        "主星": stars,
        "命主": mingzhu,
        "身主": shenzhu,
        "四化": {"化禄": sihua[0], "化权": sihua[1], "化科": sihua[2], "化忌": sihua[3]},
        "命宫干支": GAN_LIST[((WUHU_DUN[yg] + (ming_gong - 2)) % 10)] + ZHI_GONG[ming_gong],
    }

# ---------------- 汉字五行词典（精简内置 + references 扩展） ----------------

WUXING_HANZI = {}

def load_wuxing_dict():
    """加载汉字五行词典：优先 references/wuxing-hanzi.md，失败则用内置精简版。"""
    here = os.path.dirname(os.path.abspath(__file__))
    ref = os.path.join(os.path.dirname(here), "references", "wuxing-hanzi.md")
    if os.path.exists(ref):
        with open(ref, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    ch, wx = parts[0], parts[1]
                    if len(ch) == 1 and wx in "金木水火土":
                        WUXING_HANZI[ch] = wx
    if not WUXING_HANZI:
        WUXING_HANZI.update(_BUILTIN_WX)

# 内置精简词典（仅在 references 缺失时兜底）
_BUILTIN_WX = {
    "天":"金","地":"土","人":"金","大":"火","小":"金","中":"火","山":"土","水":"水","风":"木","云":"水",
    "日":"火","月":"水","星":"金","光":"火","明":"火","文":"水","武":"水","英":"木","雄":"水","杰":"木",
    "子":"水","安":"土","宁":"火","平":"水","和":"土","乐":"火","福":"水","禄":"火","寿":"金","喜":"水",
    "嘉":"木","祥":"金","瑞":"金","祺":"木","欣":"木","悦":"金","怡":"土","然":"金","雅":"木","韵":"土",
    "诗":"金","书":"金","画":"土","琴":"木","棋":"木","梅":"木","兰":"木","竹":"木","菊":"木",
    "松":"木","柏":"木","桂":"木","楠":"木","桐":"木","枫":"木","林":"木","森":"木","源":"水","泉":"水",
    "海":"水","涛":"水","波":"水","澜":"水","溪":"水","浩":"水","瀚":"水","泽":"水","润":"水","清":"水",
    "冰":"水","雪":"水","霜":"水","露":"水","雨":"水","雷":"木","霆":"水","震":"水","虹":"水","霞":"水",
    "玉":"金","金":"金","银":"金","宝":"金","珠":"金","琳":"木","瑶":"火","瑾":"火","瑜":"金","琪":"木",
    "珊":"金","瑚":"金","琦":"木","琬":"土","玮":"土","珩":"水","玟":"水","玥":"土","珺":"木",
    "宇":"土","宙":"金","宏":"水","远":"土","达":"火","飞":"水","腾":"火","翔":"土","鹏":"水","鹤":"水",
    "凤":"水","龙":"土","虎":"水","骏":"金","志":"火","毅":"木","勇":"土","强":"木","刚":"金","健":"木",
    "康":"木","泰":"火","盛":"金","昌":"金","国":"木","家":"木","华":"水","夏":"火","春":"木","秋":"金",
    "冬":"水","思":"金","念":"火","恩":"土","德":"火","仁":"金","义":"木","礼":"火","智":"火","信":"金",
    "诚":"金","忠":"火","孝":"水","谦":"木","勤":"木","俭":"木","善":"金","美":"水","丽":"火","婉":"土",
    "娴":"土","淑":"水","慧":"水","敏":"水","捷":"金","颖":"木","秀":"金","娟":"木","婷":"火","娇":"木",
    "娜":"火","妍":"水","嫣":"土","芙":"木","蓉":"木","薇":"木","萱":"木","芷":"木","若":"木","芸":"木",
    "芹":"木","青":"金","蓝":"木","碧":"水","翠":"金","丹":"火","彤":"火","红":"水","紫":"金","黛":"火",
    "雯":"水","霭":"水","曦":"火","晟":"火","昊":"火","昱":"火","煜":"火","炜":"火","烨":"火","烁":"金",
    "灿":"火","焕":"火","旭":"木","昂":"火","昶":"火","晏":"土","晴":"火","暄":"火","暖":"火","曜":"火",
    "恒":"水","屹":"土","峥":"土","嵘":"土","巍":"土","岩":"土","岳":"土","峰":"土","岭":"土","川":"金",
    "河":"水","江":"水","湖":"水","泊":"水","沐":"水","沛":"水","沁":"水","洺":"水","潇":"水","漪":"水",
    "淳":"水","涵":"水","淇":"水","添":"水","淼":"水","渊":"水","渝":"水","澄":"水","澈":"水",
    "灵":"火","程":"火","锦":"金","铭":"金","锋":"金","钧":"金","铁":"金","锟":"金","钢":"金","锐":"金",
    "鉴":"金","鑫":"金","铄":"金","钦":"金","键":"金","镇":"金","铮":"金","铜":"金","楚":"木","梦":"木",
    "梓":"木","棠":"木","榆":"木","榕":"木","槿":"木","檀":"木","柏":"木","柳":"木","桃":"木","梨":"木",
    "杏":"木","樾":"木","栩":"木","楷":"木","枢":"木","棋":"木","栋":"木","梁":"木","楠":"木","梧":"木",
}

LUCK = {}

def load_luck():
    """字义吉凶：优先 references/hanzi-luck.md（吉/中/凶），失败则空。"""
    global LUCK
    here = os.path.dirname(os.path.abspath(__file__))
    ref = os.path.join(os.path.dirname(here), "references", "hanzi-luck.md")
    if os.path.exists(ref):
        with open(ref, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) >= 2 and len(parts[0]) == 1:
                    LUCK[parts[0]] = parts[1]

# 常见度标注（高频起名用字 => 常见；否则 适中/生僻 由笔画数粗判）
COMMON_NAMING = set("梓萱浩然宇轩子涵欣怡诗涵梦琪思远明轩一诺晨曦若曦语嫣沐宸宇航嘉懿泽宇铭轩文昊俊杰雨桐欣妍雅静思彤佳怡欣悦天翊铭泽梓涵雨泽子墨承宇芷若芸熙清扬")

# 常见爆款字（重名率提示）
OVERUSED = set("梓萱浩然宇轩子涵欣怡诗涵梦琪思远明轩一诺晨曦若曦语嫣沐宸宇航嘉懿泽宇铭轩文昊雨桐欣妍雅静思彤佳怡欣悦")

# ---------------- 风格字库（五行均衡版，gender 区分） ----------------
# 五行由喜用神决定候选范围，风格只在范围内做气质排序；古风/现代/中性均为气质标签
STYLE_WORDS = {
    "classical": {
        "male": set("钧铭锡铮钰钟铎鉴锐铠彬楠桓柯棠楷森楚柏渊瀚泽泓澄沐沛澜涛煜烨昭旭炳焕晟曜曦岳嵩峻崇坤峥磊磐屹"),
        "female": set("雅韵诗书琴棋梅兰竹菊松柏桂楠桐枫林森芙芷芸薇兰清溪澜瀚泽润淑婉娴慧泓沐沛涵煜烨昭旭晏晴彤雯锦钰铃钗珊银玉珠铮铭恩安"),
    },
    "modern": set("宸宇轩梓涵沐熙语嫣欣妍若曦晨曦明轩一诺"),
    "neutral": set("安然平和乐福瑞祥祺嘉欣悦怡然雅韵思恩德仁礼智信诚忠谦勤俭善美"),
}

def style_tag_of(ch, gender="male"):
    """按风格字库返回该字的气质标签（古风/现代/中性）。"""
    for style, words in STYLE_WORDS.items():
        pool = words.get(gender, set()) if isinstance(words, dict) else words
        if ch in pool:
            return {"classical": "古风", "modern": "现代", "neutral": "中性"}[style]
    return "中性"

# ---------------- 时代高频字（重名率与时代感标签） ----------------
ERA_NAMING = {
    "60后": set("军国建强志伟芳秀丽敏静红霞梅兰玉春桂爱平"),
    "70后": set("勇杰涛明华刚辉艳娟玲燕磊丽敏秀霞平海东"),
    "80后": set("磊鹏超鑫洋浩婷倩雪蕾娜丹帅萌晨阳凯文斌"),
    "90后": set("宇轩俊杰子涵欣怡思彤雨悦嘉懿诗琪梦洁俊楠"),
    "00后": set("梓萱浩然奕辰铭泽语嫣若汐雨桐子墨一诺皓轩"),
}

def era_tag_of(name):
    """统计两字在各年代高频字集合的命中数，返回最贴合的时代标签。"""
    best, best_n = "跨代通用", 0
    for era, words in ERA_NAMING.items():
        n = sum(1 for c in name if c in words)
        if n > best_n:
            best, best_n = era, n
    return best

# ---------------- 精简拼音表（双声叠韵检测，覆盖起名高频字） ----------------
# 格式: 字 -> (声母, 韵母)；声母为空串表示零声母
_PY = {
    "田":("t","ian"),
    "天":("t","ian"),"明":("m","ing"),"文":("w","en"),"宇":("","yu"),"轩":("x","uan"),
    "子":("z","i"),"涵":("h","an"),"欣":("x","in"),"怡":("y","i"),"诗":("sh","i"),
    "琪":("q","i"),"梦":("m","eng"),"思":("s","i"),"远":("y","uan"),"浩":("h","ao"),
    "然":("r","an"),"泽":("z","e"),"铭":("m","ing"),"锋":("f","eng"),"钧":("j","un"),
    "锦":("j","in"),"瑞":("r","ui"),"嘉":("j","ia"),"祥":("x","iang"),"梓":("z","i"),
    "萱":("x","uan"),"语":("y","u"),"嫣":("y","an"),"若":("r","uo"),"曦":("x","i"),
    "晨":("ch","en"),"一":("y","i"),"诺":("n","uo"),"沐":("m","u"),"宸":("ch","en"),
    "航":("h","ang"),"俊":("j","un"),"杰":("j","ie"),"昊":("h","ao"),"晟":("sh","eng"),
    "烨":("y","e"),"煜":("y","u"),"昭":("zh","ao"),"旭":("x","u"),"炳":("b","ing"),
    "焕":("h","uan"),"曜":("y","ao"),"岳":("y","ue"),"嵩":("s","ong"),"峻":("j","un"),
    "崇":("ch","ong"),"坤":("k","un"),"峥":("zh","eng"),"磊":("l","ei"),"磐":("p","an"),
    "屹":("y","i"),"彬":("b","in"),"楠":("n","an"),"桓":("h","uan"),"柯":("k","e"),
    "棠":("t","ang"),"楷":("k","ai"),"森":("s","en"),"楚":("ch","u"),"柏":("b","ai"),
    "渊":("y","uan"),"瀚":("h","an"),"泓":("h","ong"),"澄":("ch","eng"),"沛":("p","ei"),
    "澜":("l","an"),"涛":("t","ao"),"鉴":("j","ian"),"锐":("r","ui"),"铠":("k","ai"),
    "铮":("zh","eng"),"锡":("x","i"),"钰":("y","u"),"钟":("zh","ong"),"铎":("d","uo"),
    "宏":("h","ong"),"达":("d","a"),"飞":("f","ei"),"腾":("t","eng"),"翔":("x","iang"),
    "鹏":("p","eng"),"鹤":("h","e"),"龙":("l","ong"),"峰":("f","eng"),"岩":("y","an"),
    "川":("ch","uan"),"江":("j","iang"),"海":("h","ai"),"洋":("y","ang"),"波":("b","o"),
    "霖":("l","in"),"寰":("h","uan"),"刚":("g","ang"),"毅":("y","i"),"勇":("y","ong"),
    "强":("q","iang"),"健":("j","ian"),"康":("k","ang"),"泰":("t","ai"),"盛":("sh","eng"),
    "昌":("ch","ang"),"志":("zh","i"),"伟":("w","ei"),"国":("g","uo"),"华":("h","ua"),
    "军":("j","un"),"建":("j","ian"),"平":("p","ing"),"辉":("h","ui"),"艳":("y","an"),
    "娟":("j","uan"),"玲":("l","ing"),"兰":("l","an"),"燕":("y","an"),"芳":("f","ang"),
    "秀":("x","iu"),"丽":("l","i"),"敏":("m","in"),"静":("j","ing"),"红":("h","ong"),
    "霞":("x","ia"),"梅":("m","ei"),"雅":("y","a"),"韵":("y","un"),"书":("sh","u"),
    "琴":("q","in"),"棋":("q","i"),"竹":("zh","u"),"菊":("j","u"),"松":("s","ong"),
    "桂":("g","ui"),"桐":("t","ong"),"枫":("f","eng"),"林":("l","in"),"芙":("f","u"),
    "芷":("zh","i"),"芸":("y","un"),"薇":("w","ei"),"清":("q","ing"),"溪":("x","i"),
    "润":("r","un"),"淑":("sh","u"),"婉":("w","an"),"娴":("x","ian"),"慧":("h","ui"),
    "沁":("q","in"),"添":("t","ian"),"淳":("ch","un"),"澈":("ch","e"),"熙":("x","i"),
    "妍":("y","an"),"汐":("x","i"),"彤":("t","ong"),"雯":("w","en"),"雪":("x","ue"),
    "冰":("b","ing"),"霜":("sh","uang"),"露":("l","u"),"雨":("y","u"),"雷":("l","ei"),
    "霆":("t","ing"),"震":("zh","en"),"虹":("h","ong"),"晴":("q","ing"),"暄":("x","uan"),
    "暖":("n","uan"),"昶":("ch","ang"),"晏":("y","an"),"昱":("y","u"),"炜":("w","ei"),
    "烁":("sh","uo"),"灿":("c","an"),"灵":("l","ing"),"程":("ch","eng"),"樾":("y","ue"),
    "栩":("x","u"),"榆":("y","u"),"榕":("r","ong"),"槿":("j","in"),"檀":("t","an"),
    "柳":("l","iu"),"桃":("t","ao"),"梨":("l","i"),"杏":("x","ing"),"栋":("d","ong"),
    "梁":("l","iang"),"梧":("w","u"),"铄":("sh","uo"),"钦":("q","in"),"键":("j","ian"),
    "镇":("zh","en"),"铜":("t","ong"),"鑫":("x","in"),"钢":("g","ang"),"铁":("t","ie"),
    "锟":("k","un"),"银":("y","in"),"玉":("y","u"),"金":("j","in"),"宝":("b","ao"),
    "珠":("zh","u"),"琳":("l","in"),"瑶":("y","ao"),"瑾":("j","in"),"瑜":("y","u"),
    "珊":("sh","an"),"瑚":("h","u"),"琦":("q","i"),"琬":("w","an"),"玮":("w","ei"),
    "珩":("h","eng"),"玟":("w","en"),"玥":("y","ue"),"珺":("j","un"),"安":("","an"),
    "宁":("n","ing"),"平":("p","ing"),"和":("h","e"),"乐":("l","e"),"福":("f","u"),
    "禄":("l","u"),"寿":("sh","ou"),"喜":("x","i"),"祺":("q","i"),"悦":("y","ue"),
    "恩":("","en"),"德":("d","e"),"仁":("r","en"),"礼":("l","i"),"智":("zh","i"),
    "信":("x","in"),"诚":("ch","eng"),"忠":("zh","ong"),"孝":("x","iao"),"谦":("q","ian"),
    "勤":("q","in"),"俭":("j","ian"),"善":("sh","an"),"美":("m","ei"),"亦":("y","i"),
    "可":("k","e"),"若":("r","uo"),"星":("x","ing"),"月":("y","ue"),"阳":("y","ang"),
    "嘉":("j","ia"),"欣":("x","in"),"睿":("r","ui"),"硕":("sh","uo"),"凡":("f","an"),
    "帆":("f","an"),"颂":("s","ong"),"朗":("l","ang"),"峻":("j","un"),"骐":("q","i"),
    "麟":("l","in"),"凯":("k","ai"),"扬":("y","ang"),"澈":("ch","e"),"晗":("h","an"),
}

def py_of(ch):
    return _PY.get(ch)

# ---------------- 三才五格 ----------------

STROKE = {}

def load_stroke():
    """笔画数：优先内置，大字典中可再扩展。"""
    global STROKE
    here = os.path.dirname(os.path.abspath(__file__))
    ref = os.path.join(os.path.dirname(here), "references", "strokes.md")
    if os.path.exists(ref):
        with open(ref, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) >= 2 and len(parts[0]) == 1:
                    STROKE[parts[0]] = int(parts[1])
    if not STROKE:
        _init_builtin_stroke()

def _init_builtin_stroke():
    """内置常见姓氏与起名高频字笔画（简体）。"""
    for ch, n in {
        "王":4,"李":7,"张":7,"刘":6,"陈":7,"杨":7,"黄":11,"赵":9,"吴":7,"周":8,
        "徐":10,"孙":6,"马":3,"朱":6,"胡":9,"郭":10,"何":7,"高":10,"林":8,"罗":8,
        "郑":8,"梁":11,"谢":12,"宋":7,"唐":10,"许":6,"韩":12,"冯":5,"邓":4,"曹":11,
        "彭":12,"曾":12,"肖":7,"田":5,"董":12,"袁":10,"潘":15,"于":3,"蒋":12,"蔡":14,
        "余":7,"杜":7,"叶":5,"程":12,"苏":7,"魏":17,"吕":6,"丁":2,"任":6,"沈":7,
        "姚":9,"卢":5,"姜":9,"崔":11,"钟":9,"谭":14,"陆":7,"汪":7,"范":8,"金":8,
        "石":5,"廖":14,"贾":10,"夏":10,"韦":4,"付":5,"方":4,"白":5,"邹":7,"孟":8,
        "熊":14,"秦":10,"邱":7,"江":6,"尹":4,"薛":16,"闫":6,"段":9,"雷":13,"侯":9,
        "龙":5,"史":5,"陶":10,"黎":15,"贺":9,"顾":10,"毛":4,"郝":9,"龚":11,"邵":7,
        "万":3,"钱":10,"严":7,"覃":12,"武":8,"戴":17,"莫":10,"孔":4,"向":6,"常":11,
        "天":4,"地":6,"人":2,"大":3,"小":3,"中":4,"山":3,"水":4,"风":4,"云":4,
        "日":4,"月":4,"星":9,"光":6,"明":8,"文":4,"武":8,"英":8,"雄":12,"杰":8,
        "子":3,"安":6,"宁":5,"平":5,"和":8,"乐":5,"福":13,"禄":12,"寿":7,"喜":12,
        "嘉":14,"祥":10,"瑞":13,"祺":12,"欣":8,"悦":10,"怡":8,"然":12,"雅":12,"韵":13,
        "诗":8,"书":4,"画":8,"琴":12,"棋":12,"梅":11,"兰":5,"竹":6,"菊":11,
        "松":8,"柏":9,"桂":10,"楠":13,"桐":10,"枫":8,"林":8,"森":12,"源":13,"泉":9,
        "海":10,"涛":10,"波":8,"澜":15,"溪":13,"浩":10,"瀚":19,"泽":8,"润":10,"清":11,
        "冰":6,"雪":11,"霜":17,"露":21,"雨":8,"雷":13,"霆":14,"震":15,"虹":9,"霞":17,
        "玉":5,"金":8,"银":11,"宝":8,"珠":10,"琳":12,"瑶":14,"瑾":15,"瑜":13,"琪":12,
        "珊":9,"瑚":13,"琦":12,"琬":12,"玮":8,"珩":10,"玟":8,"玥":9,"珺":11,
        "宇":6,"宙":8,"宏":7,"远":7,"达":6,"飞":3,"腾":13,"翔":12,"鹏":13,"鹤":15,
        "凤":4,"龙":5,"骏":10,"志":7,"毅":15,"勇":9,"强":12,"刚":6,"健":10,"康":11,
        "泰":10,"盛":11,"昌":8,"国":8,"家":10,"华":6,"夏":10,"春":9,"秋":9,"冬":5,
        "思":9,"念":8,"恩":10,"德":15,"仁":4,"义":3,"礼":5,"智":12,"信":9,"诚":8,
        "忠":8,"孝":7,"谦":12,"勤":13,"俭":9,"善":12,"美":9,"丽":7,"婉":11,"娴":10,
        "淑":11,"慧":15,"敏":11,"捷":11,"颖":13,"秀":7,"娟":10,"婷":12,"娇":9,"娜":9,
        "妍":7,"嫣":14,"芙":7,"蓉":13,"薇":16,"萱":12,"芷":7,"若":8,"芸":7,"芹":7,
        "青":8,"蓝":13,"碧":14,"翠":14,"丹":4,"彤":7,"红":6,"紫":12,"黛":17,
        "雯":12,"霭":19,"曦":20,"晟":10,"昊":8,"昱":9,"煜":13,"炜":8,"烨":10,"烁":9,
        "灿":7,"焕":11,"旭":6,"昂":8,"昶":9,"晏":10,"晴":12,"暄":13,"暖":13,"曜":18,
        "恒":9,"屹":6,"峥":9,"嵘":14,"巍":20,"岩":8,"岳":8,"峰":10,"岭":8,"川":3,
        "河":8,"江":6,"湖":12,"泊":8,"沐":7,"沛":7,"沁":7,"洺":9,"潇":14,"漪":14,
        "淳":11,"涵":11,"淇":11,"添":11,"淼":12,"渊":11,"渝":12,"澄":15,"澈":15,
        "灵":7,"程":12,"锦":13,"铭":11,"锋":12,"钧":9,"铁":10,"锟":12,"钢":9,"锐":12,
        "鉴":13,"鑫":24,"铄":10,"钦":9,"键":13,"镇":15,"铮":11,"铜":11,"楚":13,"梦":11,
        "梓":11,"棠":12,"榆":13,"榕":14,"槿":15,"檀":17,"柏":9,"柳":9,"桃":10,"梨":11,
        "杏":7,"樾":15,"栩":10,"楷":13,"枢":8,"栋":9,"梁":11,"梧":11,"楠":13,
    }.items():
        STROKE[ch] = n

def sankai_score(surname, given):
    """三才五格：返回各格数与吉凶。"""
    if not surname or surname == "无":
        return None
    s_stroke = sum(STROKE.get(c, 0) for c in surname)
    g_stroke = sum(STROKE.get(c, 0) for c in given)
    if s_stroke == 0 or g_stroke == 0:
        return None
    tian = s_stroke + 1
    ren = s_stroke + STROKE.get(given[0], 0)
    di = g_stroke + 1 if len(given) == 1 else sum(STROKE.get(c, 0) for c in given) + 1
    zong = s_stroke + g_stroke
    wai = zong - ren + 1
    def jx(n):
        return SHU_LI.get(n, "半吉")
    return {
        "天格": (tian, jx(tian)),
        "人格": (ren, jx(ren)),
        "地格": (di, jx(di)),
        "外格": (wai, jx(wai)),
        "总格": (zong, jx(zong)),
    }

# ---------------- 卦象（梅花易数简化：姓名笔画起卦） ----------------

GUA_NAME = [
    "乾","兑","离","震","巽","坎","艮","坤"
]
GUA_BRIEF = {
    "乾":"天行健，自强不息",
    "兑":"丽泽相悦，和乐交流",
    "离":"明两作，光明相继",
    "震":"洊雷，警醒奋发",
    "巽":"随风，柔顺入微",
    "坎":"习坎，险中有信",
    "艮":"兼山，止静笃实",
    "坤":"地势坤，厚德载物"
}

def gua_result(surname, given):
    s_stroke = sum(STROKE.get(c, 0) for c in surname)
    g_stroke = sum(STROKE.get(c, 0) for c in given)
    if s_stroke == 0 or g_stroke == 0:
        return None
    up = (s_stroke + g_stroke) % 8
    down = g_stroke % 8
    up_gua = GUA_NAME[up] if up > 0 else "坤"
    down_gua = GUA_NAME[down] if down > 0 else "坤"
    return f"{up_gua}{down_gua}", GUA_BRIEF.get(up_gua, "") + " · " + GUA_BRIEF.get(down_gua, "")

# ---------------- 音韵 ----------------

def yinyun(given):
    tones = [get_tone(c) for c in given]
    if not all(tones):
        return "音韵未知"
    # 平仄
    pb = ["平" if t in (1, 2) else "仄" for t in tones]
    parts = []
    # 双声（声母相同）/ 叠韵（韵母相同）检测
    pys = [py_of(c) for c in given]
    if all(pys) and len(pys) > 1:
        initials = [p[0] for p in pys]
        finals = [p[1] for p in pys]
        if len(set(initials)) == 1 and initials[0] != "":
            parts.append("双声")
        if len(set(finals)) == 1:
            parts.append("叠韵")
    # 同调 / 起伏
    if len(set(tones)) == 1:
        parts.append("同调流畅")
    elif len(set(tones)) == len(tones):
        parts.append("起伏有致")
    else:
        parts.append("".join(pb) + "搭配")
    return f"声调{'、'.join(str(t) for t in tones)}，{'、'.join(parts)}"

# ---------------- 候选名生成 ----------------

POETRY_NAMES = []
CHARACTERS = {}
NAME_STATS = {}
SENSITIVE = {}

def load_characters():
    """加载常用起名汉字库，用于过滤生僻或缺少基础信息的字。"""
    global CHARACTERS
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data", "characters.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            CHARACTERS = json.load(f)

def load_name_stats():
    """加载由 build_name_stats.py 生成的可选姓名语料统计。"""
    global NAME_STATS
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data", "name_stats.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            NAME_STATS = json.load(f).get("records", {})

def load_sensitive():
    """加载敏感词和谐音组合库。"""
    global SENSITIVE
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data", "sensitive_words.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            SENSITIVE = json.load(f)

def sensitive_match(full_name):
    """返回敏感/不良谐音说明；无命中时返回 None。"""
    if full_name in SENSITIVE.get("bad_combinations", []):
        return f"命中敏感组合：{full_name}"
    pinyin = "".join(CHARACTERS.get(char, {}).get("pinyin", "") for char in full_name)
    for bad_pinyin in SENSITIVE.get("homophones", {}):
        if bad_pinyin and bad_pinyin in pinyin:
            return f"可能谐音：{bad_pinyin}"
    return None

def corpus_match(name, gender="neutral"):
    """返回给定名的常见度和性别倾向，仅作统计参考。"""
    item = NAME_STATS.get(name)
    if not item:
        return {"count": 0, "popularity": "未收录", "gender": "未知"}
    total = item.get("count", 0)
    male, female, unknown = item.get("male", 0), item.get("female", 0), item.get("unknown", 0)
    known = male + female
    if known == 0:
        tendency = "未知"
    elif max(male, female) / known < 0.65:
        tendency = "中性/混合"
    else:
        tendency = "偏男" if male > female else "偏女"
    if total >= 100:
        popularity = "较常见"
    elif total >= 30:
        popularity = "中等"
    else:
        popularity = "较少见"
    return {"count": total, "popularity": popularity, "gender": tendency}

def load_poetry_names():
    """加载诗词名字库；数据缺失时仍可使用字库生成名字。"""
    global POETRY_NAMES
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data", "poetry_names.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            POETRY_NAMES = json.load(f)

def load_classics(root):
    """加载用户本地经典原文，返回可供候选名检索的行记录。"""
    if not root:
        return []
    root_path = Path(root).expanduser().resolve()
    if not root_path.exists():
        raise FileNotFoundError(f"经典原文目录不存在：{root_path}")
    records = []
    for path in sorted(root_path.rglob("*.txt")):
        try:
            lines = path.read_text(encoding="utf-8-sig").splitlines()
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(lines, 1):
            text = line.strip()
            if text:
                records.append({
                    "source": f"{path.relative_to(root_path)}:{number}",
                    "text": text,
                })
    return records

def poetry_match(name, classics=None):
    """返回名字库中与候选名完全匹配的出处信息。"""
    for item in POETRY_NAMES:
        if item.get("name") == name:
            return {
                "source": item.get("source", ""),
                "quote": item.get("quote", ""),
                "meaning": item.get("meaning", "")
            }
    single_sources = {
        "安": {"source": "《道德经》第八十章", "quote": "安其居，乐其俗", "meaning": "安定自得、内心从容"},
        "亦": {"source": "《楚辞·离骚》", "quote": "亦余心之所善兮", "meaning": "坚持内心所珍视的美好"},
        "修": {"source": "《楚辞·离骚》", "quote": "路漫漫其修远兮", "meaning": "修身自持、志向长远"},
        "远": {"source": "《楚辞·离骚》", "quote": "路漫漫其修远兮", "meaning": "目光长远、行路致远"},
        "清": {"source": "《楚辞·渔父》", "quote": "举世皆浊我独清", "meaning": "清正自守、澄澈明朗"},
        "昭": {"source": "《诗经·大雅·既醉》", "quote": "昭明有融", "meaning": "光明通达、明德昭著"},
        "和": {"source": "《道德经》第四十二章", "quote": "冲气以为和", "meaning": "和合平衡、温厚通达"},
        "山": {"source": "《诗经·小雅·车舝》", "quote": "高山仰止，景行行止", "meaning": "稳重高远、令人敬仰"},
        "嘉": {"source": "《诗经·小雅·南有嘉鱼》", "quote": "南有嘉鱼，烝然罩罩", "meaning": "美善可嘉、温润有礼"},
        "穆": {"source": "《诗经·大雅·烝民》", "quote": "穆如清风", "meaning": "端庄温厚、清雅从容"},
    }
    if len(name) == 1 and name in single_sources:
        return single_sources[name]
    if classics and len(name) > 1:
        for item in classics:
            if name in item["text"]:
                return {
                    "source": item["source"],
                    "quote": item["text"],
                    "meaning": "本地经典原文检索命中，请结合上下文核对寓意"
                }
    return None

def gen_candidates(surname, gender, taboo, generation, style, xi, count=10,
                   name_length=2, classics=None):
    """基于喜用五行、性别、中性偏好和风格生成单名或双名。"""
    cands = []
    # 性别倾向
    if gender == "male":
        prefer = set("刚毅勇强健康泰盛昌志宏远达飞腾翔鹏鹤峰岩岳川江海洋涛波霖宇寰坤昊昱晟曦烨烁铭锋锐钧")
        exclude = set("婉娴淑慧敏秀娟婷娇娜妍嫣芙蓉薇萱芷若芸青蓝碧翠丹彤红紫黛雯霭雪兰梅菊诗琴棋书画悦怡欣")
    elif gender == "female":
        prefer = set("婉娴淑慧敏秀娟婷娇娜妍嫣芙蓉薇萱芷若芸青蓝碧翠丹彤红紫黛雯霭雪兰梅菊诗琴棋书画悦怡欣")
        exclude = set("刚毅勇强健康泰盛昌志宏远达飞腾翔鹏鹤峰岩岳川江海洋涛波霖宇寰坤昊昱晟曦烨烁铭锋锐钧")
    else:
        prefer = set("安宁和清昭修穆远知简澄明朗嘉景恒允亦初言川云山溪")
        exclude = set()
    chars = sorted(WUXING_HANZI.keys(), key=lambda c: -STROKE.get(c, 0))
    # 过滤
    pool = []
    for ch in chars:
        if CHARACTERS and ch not in CHARACTERS:
            continue
        if gender == "neutral" and CHARACTERS:
            metadata = CHARACTERS.get(ch, {})
            categories = set(metadata.get("category", []))
            if categories & {"男名常用", "女名常用"}:
                continue
            if ch in "艳娇娜婷妍婉娴衣":
                continue
            if style in {"classical", "neutral"}:
                quality_categories = {
                    "古典", "清雅", "大气", "稳重", "平安", "和谐", "美玉",
                    "宏大", "美德", "光明", "显著", "品德", "明朗", "通用"
                }
                if not categories.intersection(quality_categories):
                    continue
        if taboo and any(t in ch for t in taboo):
            continue
        if ch in exclude:
            continue
        pool.append(ch)
    # 风格（气质排序：五行由喜用神决定范围，风格只在范围内调优）
    if style in STYLE_WORDS:
        words = STYLE_WORDS[style]
        prefer |= words.get(gender, set()) if isinstance(words, dict) else words

    pool_sorted = sorted(pool, key=lambda c: (
        WUXING_HANZI.get(c) != xi,
        c not in prefer,
        -STROKE.get(c, 0)
    ))
    used = set()
    if name_length == 1:
        for char in pool_sorted:
            if len(cands) >= count * 6:
                break
            if generation and generation != char:
                continue
            name = char
            if sensitive_match(surname + name):
                continue
            score = 30 if xi and WUXING_HANZI[char] == xi else 0
            reasons = [f"单字属{xi}参考"] if xi else ["出生时辰未知，未使用喜用五行筛选"]
            sk = sankai_score(surname, name)
            if sk:
                good = sum(1 for value in sk.values() if value[1] == "吉")
                score += good * 5
                reasons.append(f"三才五格{good}个吉格")
            if char in prefer:
                score += 5
            luck_note = [f"{char}({LUCK[char]})"] if char in LUCK else []
            if LUCK.get(char) != "凶":
                score += 5
            poetry = poetry_match(name, classics)
            corpus = corpus_match(name, gender)
            score = min(score, 100)
            cands.append({
                "name": name, "full": surname + name, "score": score,
                "wuxing": WUXING_HANZI[char], "reasons": reasons,
                "common": "常见" if char in OVERUSED else "适中",
                "style_tag": style_tag_of(char, gender),
                "era_tag": era_tag_of(name), "yinyun": yinyun(surname + name),
                "sankai": sk, "gua": gua_result(surname, name),
                "luck": luck_note, "poetry": poetry,
                "meaning": CHARACTERS.get(char, {}).get("meaning", ""),
                "corpus": corpus
            })
        cands.sort(key=lambda x: -x["score"])
        return cands[:count]

    first_count = {}
    second_count = {}
    for first in pool_sorted[:60]:
        for second in pool_sorted[:60]:
            if len(cands) >= count * 6:
                break
            if first == second:
                continue
            if generation and generation != first:
                continue
            if first_count.get(first, 0) >= 2:
                continue
            if second_count.get(second, 0) >= 2:
                continue
            name = first + second
            if name in used:
                continue
            if sensitive_match(surname + name):
                continue
            used.add(name)
            # 打分
            score = 0
            reasons = []
            if WUXING_HANZI[first] == xi:
                score += 30
                reasons.append(f"首字属{xi}补缺")
            if WUXING_HANZI[second] == xi:
                score += 30
                reasons.append(f"次字属{xi}补缺")
            sk = sankai_score(surname, name)
            if sk:
                good = sum(1 for k, v in sk.items() if v[1] == "吉")
                score += good * 5
                reasons.append(f"三才五格{good}个吉格")
            g = gua_result(surname, name)
            if g:
                score += 3
                reasons.append(f"卦象{g[0]}")
            if first in prefer:
                score += 5
            if second in prefer:
                score += 5
            common = sum(1 for c in name if c in OVERUSED)
            if common == 0:
                score += 4
            luck_note = []
            for c in name:
                if c in LUCK:
                    luck_note.append(f"{c}({LUCK[c]})")
            good_luck = sum(1 for c in name if LUCK.get(c) == "吉")
            bad_luck = sum(1 for c in name if LUCK.get(c) == "凶")
            if bad_luck == 0:
                score += 5
                reasons.append(f"字义无凶字")
            score += good_luck * 3
            if luck_note:
                reasons.append("字义吉凶:" + " ".join(luck_note))
            poetry = poetry_match(name, classics)
            corpus = corpus_match(name, gender)
            if poetry:
                score += 6
                reasons.append("诗词名字库有对应出处")
            score = min(score, 100)
            cands.append({
                "name": name,
                "full": surname + name,
                "score": score,
                "wuxing": f"{WUXING_HANZI[first]}{WUXING_HANZI[second]}",
                "reasons": reasons,
                "common": "常见" if common > 1 else ("适中" if common == 1 else "生僻"),
                "style_tag": style_tag_of(first, gender),
                "era_tag": era_tag_of(name),
                "yinyun": yinyun(surname + name),
                "sankai": sankai_score(surname, name),
                "gua": gua_result(surname, name),
                "luck": luck_note,
                "poetry": poetry,
                "meaning": "；".join(
                    CHARACTERS.get(c, {}).get("meaning", "") for c in name
                    if CHARACTERS.get(c, {}).get("meaning", "")
                ),
                "corpus": corpus
            })
            first_count[first] = first_count.get(first, 0) + 1
            second_count[second] = second_count.get(second, 0) + 1
        if len(cands) >= count * 6:
            break
    cands.sort(key=lambda x: -x["score"])
    return cands[:count]

# ---------------- 交互模式 ----------------

def interactive():
    print("=== 生辰起名 · 综合排盘系统 ===")
    birth = input("出生日期时间（如 2024-05-20 14:30，公历/农历均可）：").strip()
    cal = input("历法（gregorian公历/lunar农历，默认公历）：").strip() or "gregorian"
    gender = input("性别（male男/female女/neutral中性）：").strip() or "neutral"
    surname = input("姓氏（必填，可填'无'跳过三才）：").strip()
    taboo = input("避讳字（逗号分隔，可空）：").strip()
    generation = input("字辈（可空）：").strip()
    style = input("风格（classical古风/modern现代/neutral中性，可空）：").strip() or "neutral"
    name_length = int(input("名字长度（1单名/2双名，默认2）：").strip() or "2")
    try:
        y, mo, d, h, _minute, hour_provided = parse_birth(birth)
    except ValueError as error:
        print(f"日期格式错误：{error}")
        return
    if cal.startswith("l"):
        dt = lunar_to_solar(y, mo, d)
        y, mo, d = dt.year, dt.month, dt.day
    result = run(y, mo, d, h, gender, surname, taboo, generation, style,
                 name_length=name_length, hour_provided=hour_provided)
    print(format_human(result))

def run(y, mo, d, h, gender, surname, taboo, generation, style, count=10,
        name_length=2, hour_provided=True, classics_root=None):
    load_wuxing_dict()
    load_stroke()
    load_luck()
    load_tones()
    load_poetry_names()
    load_characters()
    load_name_stats()
    load_sensitive()
    classics = load_classics(classics_root)
    bazi = build_bazi(y, mo, d, h)
    stats, detail = wuxing_stats(bazi)
    xi, strength = xiyongshen(bazi) if hour_provided else (None, "未判定")
    ziwei = ziwei_pan(y, mo, d, h)
    cands = gen_candidates(surname, gender, taboo, generation, style, xi, count,
                           name_length, classics)
    # 生肖
    sx = SHENGXIAO[((y - 4) % 12)]
    ziwei_note = ""
    if not hour_provided:
        ziwei_note = "未提供出生时辰；时柱暂按子时占位，八字喜用神与紫微结果不可视为精确结论。"
    surname_note = ""
    if not surname or surname == "无":
        surname_note = "未提供姓氏，已跳过三才五格与卦象评分（候选名仍按五行/风格生成）；补充姓氏后可获得完整评分。"
    return {
        "bazi": bazi,
        "lunar": solar_to_lunar(y, mo, d),
        "wuxing_stats": stats,
        "wuxing_detail": detail,
        "day_master": bazi["日柱"][0],
        "strength": strength,
        "xiyongshen": xi,
        "hour_unknown": not hour_provided,
        "shengxiao": sx,
        "ziwei": ziwei,
        "ziwei_note": ziwei_note,
        "surname_note": surname_note,
        "candidates": cands
    }

def format_human(result):
    """将 run 结果转为人读文本（供命令行默认输出）。"""
    lines = []
    b = result["bazi"]
    lunar = result["lunar"]
    lines.append("=== 生辰起名 · 综合排盘 ===")
    bazi_label = "八字（时柱占位）" if result.get("hour_unknown") else "八字"
    lines.append(f"{bazi_label}：{b['年柱'][0]}{b['年柱'][1]} {b['月柱'][0]}{b['月柱'][1]} {b['日柱'][0]}{b['日柱'][1]} {b['时柱'][0]}{b['时柱'][1]}")
    lines.append(f"农历：{lunar[0]}年{'闰' if lunar[3] else ''}{LUNAR_MONTHS[lunar[1]-1]}月{LUNAR_DAYS[lunar[2]-1]}")
    xi_label = "未判定（出生时辰未知）" if result.get("hour_unknown") else result["xiyongshen"]
    lines.append(f"日主：{result['day_master']}（{result['strength']}）  喜用五行：{xi_label}  生肖：{result['shengxiao']}")
    st = result["wuxing_stats"]
    stats_label = "五行分布（占位统计）" if result.get("hour_unknown") else "五行分布"
    lines.append(f"{stats_label}：金{st['金']} 木{st['木']} 水{st['水']} 火{st['火']} 土{st['土']}")
    if result.get("ziwei_note"):
        lines.append(f"[提示] {result['ziwei_note']}")
    if result.get("surname_note"):
        lines.append(f"[提示] {result['surname_note']}")
    z = result["ziwei"]
    if isinstance(z, dict):
        zw = "，".join(f"{k}:{v}" for k, v in list(z.items())[:6])
        lines.append(f"紫微：{zw}")
    lines.append("")
    lines.append("候选名（按综合评分排序）：")
    for i, c in enumerate(result["candidates"], 1):
        sk = c["sankai"]
        sk_str = "，".join(f"{k}{v[1]}" for k, v in sk.items()) if sk else "未算（姓氏缺）"
        lines.append(f"{i}. {c['full']}（{c['score']}分）五行{c['wuxing']} | {c['style_tag']}/{c['era_tag']}/{c['common']} | 音韵:{c['yinyun']} | {sk_str} | 卦象:{c['gua'][0] if c['gua'] else '无'}")
        if c.get("poetry"):
            p = c["poetry"]
            lines.append(f"   出处：{p.get('source', '')}；{p.get('quote', '')}")
        if c.get("meaning"):
            lines.append(f"   字义：{c['meaning']}")
        if c.get("corpus"):
            stats = c["corpus"]
            lines.append(f"   语料参考：{stats['popularity']}；性别倾向：{stats['gender']}；样本数：{stats['count']}")
        if c["reasons"]:
            lines.append(f"   评分依据：{'；'.join(c['reasons'])}")
    return "\n".join(lines)

def main():
    ap = argparse.ArgumentParser(description="生辰起名综合排盘")
    ap.add_argument("--birth", help="出生日期 2024-05-20 14:30")
    ap.add_argument("--calendar", default="gregorian", choices=["gregorian", "lunar"])
    ap.add_argument("--gender", default="neutral", choices=["male", "female", "neutral"])
    ap.add_argument("--surname", default="")
    ap.add_argument("--taboo", default="")
    ap.add_argument("--generation", default="")
    ap.add_argument("--style", default="neutral", choices=["classical", "modern", "neutral"])
    ap.add_argument("--count", type=int, default=10)
    ap.add_argument("--name-length", type=int, choices=[1, 2], default=2,
                    help="名字长度：1=单名，2=双名")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--classics-root", help="可选：本地经典原文目录")
    args = ap.parse_args()
    if not args.birth:
        interactive()
        return
    try:
        y, mo, d, h, _minute, hour_provided = parse_birth(args.birth)
    except ValueError as error:
        print(f"日期格式错误：{error}")
        sys.exit(1)
    if args.calendar == "lunar":
        dt = lunar_to_solar(y, mo, d)
        y, mo, d = dt.year, dt.month, dt.day
    result = run(y, mo, d, h, args.gender, args.surname, args.taboo,
                 args.generation, args.style, args.count, args.name_length,
                 hour_provided=hour_provided, classics_root=args.classics_root)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_human(result))

if __name__ == "__main__":
    main()
