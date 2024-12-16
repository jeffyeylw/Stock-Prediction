import json
import re

# 从文件中读取JSON数据
with open("q2tbl.json", 'r', encoding='utf-8') as f:
    data = json.load(f)

# 正则表达式匹配库名.表名的格式，支持一个或多个库名.表名对
pattern = re.compile(r'^\[(AStock[A-Za-z]+DB|[A-Za-z]+DB|[A-Za-z]+)(?:\.[A-Za-z_]+)?(?:,\s*(AStock[A-Za-z]+DB|[A-Za-z]+DB|[A-Za-z]+)(?:\.[A-Za-z_]+)?)*\]$')

# 用于存储不符合格式的related_tbl
invalid_related_tbls = []

# 遍历JSON数据
for item in data:
    for team_member in item.get('team', []):
        related_tbl = team_member.get('related_tbl')
        # 检查related_tbl是否符合格式
        if related_tbl and not pattern.match(related_tbl):
            invalid_related_tbls.append({
                'tid': item['tid'],
                'team_member_id': team_member['id'],
                'question': team_member['question'],
                'related_tbl': related_tbl
            })

# 打印不符合格式的related_tbl
for invalid_tbl in invalid_related_tbls:
    print(f"TID: {invalid_tbl['tid']}")
    print(f"Team Member ID: {invalid_tbl['team_member_id']}")
    print(f"Question: {invalid_tbl['question']}")
    print(f"Invalid related_tbl: {invalid_tbl['related_tbl']}\n")

# 如果需要将结果写入文件
with open('invalid_related_tbls.json', 'w', encoding='utf-8') as f:
    json.dump(invalid_related_tbls, f, indent=4, ensure_ascii=False)