import json
import re

# 添加错误处理和日志记录
def load_json_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"错误: 文件 {filepath} 未找到")
        return None
    except json.JSONDecodeError:
        print(f"错误: 文件 {filepath} 不是有效的JSON格式")
        return None
    except Exception as e:
        print(f"读取文件 {filepath} 时发生错误: {str(e)}")
        return None

import json
import re

def clean_sql(input_path, output_path):
    # 正则表达式模式，匹配包含在 ``` 和 ``` 之间的SQL语句
    pattern = r'(?s)```sql(.*?)```'
    
    # 读取q2sql.json文件
    with open(input_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)

    # 初始化计数器
    empty_sql_count = 0
    total_sql_count = 0

    # 遍历每个问题
    for question_team in questions:
        for convo in question_team['team']:
            original_sql = convo.get('sql', '')
            total_sql_count += 1  # 增加总SQL语句计数

            # 提取SQL语句
            match = re.search(pattern, original_sql, re.DOTALL)
            if match:
                sql = match.group(1).strip()  # 移除前后的空白字符
            else:
                sql = original_sql
            
            # 检查SQL是否为空
            if not sql.strip():
                empty_sql_count += 1  # 增加空SQL语句计数
                sql = ''  # 确保空的SQL语句被设置为空字符串
            
            # 移除所有的换行符和多余的空白字符
            sql_cleaned = ' '.join(sql.split())
            
            # 覆盖原始的sql键
            convo['sql'] = sql_cleaned

    # 打印空的SQL语句数量和总的SQL语句数量
    print(f"空的SQL语句数量：{empty_sql_count}")
    print(f"总共处理的SQL语句数量：{total_sql_count}")

    # 保存处理后的数据到新文件
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
        print(f"已清洗sql, 文件已成功保存到 {output_path}")

def submission_format(input_path, output_path):
    # 从输入文件中读取JSON数据
    with open(input_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    # 转换JSON数据
    transformed_data = []
    for team in data:
        new_team = {
            "tid": team["tid"],
            "team": []
        }
        for convo in team["team"]:
            new_convo = {
                "id": convo["id"],
                "question": convo["question"],
                "answer": convo.get("answer", "")  # 使用get方法，如果'answer'不存在则返回空字符串
            }
            new_team["team"].append(new_convo)
        transformed_data.append(new_team)
    
    # 将转换后的数据保存到输出文件
    with open(output_path, 'w', encoding='utf-8') as file:
        json.dump(transformed_data, file, ensure_ascii=False, indent=2)
        print(f"已生成submission文件, 文件已成功保存到 {output_path}")