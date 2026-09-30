#!/usr/bin/env python3
"""从本地性别姓名语料生成精简人名统计。

不把原始百万级文件放进 Skill；只保存给定名频次和性别计数，供运行时做
常见度、性别倾向和重名风险参考。
"""

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


COMMON_SURNAMES = set(
    "王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾肖田董袁潘于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦江尹薛闫段雷侯陶黎贺顾毛郝龚邵钱严覃武戴莫孔向常"
)
COMPOUND_SURNAMES = {
    "欧阳", "司马", "上官", "诸葛", "东方", "独孤", "南宫", "皇甫",
    "尉迟", "公孙", "慕容", "宇文", "长孙", "司徒", "司空", "夏侯",
    "令狐", "钟离", "闻人", "澹台", "赫连", "端木", "百里", "呼延",
}


def is_chinese_name(name):
    return bool(name) and all("\u4e00" <= char <= "\u9fff" for char in name)


def given_part(name):
    """去除常见单姓/复姓，保留名字部分。"""
    for surname in sorted(COMPOUND_SURNAMES, key=len, reverse=True):
        if name.startswith(surname) and len(name) > len(surname):
            return name[len(surname):]
    if name and name[0] in COMMON_SURNAMES and len(name) > 1:
        return name[1:]
    return ""


def build(input_path, output_path, limit):
    stats = defaultdict(lambda: {"count": 0, "gender": Counter()})
    total = 0
    valid = 0

    with input_path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.reader(handle):
            if len(row) < 2 or row[0].strip() in {"", "dict"}:
                continue
            full_name, gender = row[0].strip(), row[1].strip()
            total += 1
            if not is_chinese_name(full_name):
                continue
            given = given_part(full_name)
            if not given or len(given) not in {1, 2}:
                continue
            valid += 1
            stats[given]["count"] += 1
            stats[given]["gender"][gender] += 1

    ranked = sorted(stats.items(), key=lambda item: (-item[1]["count"], item[0]))
    records = {}
    for name, item in ranked[:limit]:
        records[name] = {
            "count": item["count"],
            "male": item["gender"].get("男", 0),
            "female": item["gender"].get("女", 0),
            "unknown": item["gender"].get("未知", 0),
        }

    output = {
        "description": "给定名频次和性别计数，仅用于常见度与性别倾向参考",
        "total_rows": total,
        "valid_given_rows": valid,
        "records": records,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {len(records)} records to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="构建精简中文姓名统计")
    parser.add_argument("input", type=Path, help="Chinese_Names_Corpus_Gender 文本文件")
    parser.add_argument("output", type=Path, help="输出 name_stats.json")
    parser.add_argument("--limit", type=int, default=100000, help="保留频次最高的名字数量")
    args = parser.parse_args()
    build(args.input, args.output, args.limit)


if __name__ == "__main__":
    main()
