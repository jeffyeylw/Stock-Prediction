import json
from zhipuai import ZhipuAI
from dotenv import load_dotenv
from utlis import load_json_file
import os

# 根据库表信息判断从哪个库提取, 把对应需要查询的库的建表信息加入Prompt,输出所需要的SQL语句,清洗SQL语句作数据库查询

load_dotenv(".env")
# C:\Users\user\Desktop\叶力维-实习\2024金融大模型挑战赛\code\

api_key = os.getenv('ZHIPU_API_KEY')
client = ZhipuAI(api_key=api_key)

def answer_questions(config):
    questions = load_json_file(config['sql_result_path'])

    sql2answer_prompt = f"""
    你现在是一个数据库专家，同时对金融行业有很深入的理解，任务是结合提供的SQL和SQL结果回答金融问题：

    要求：
    1. 请回答尽量简洁清晰
    2. 理解分析类的回答结合数据给出自己的见解
    3. 如果没有SQL结果，则直接回答“信息提取失败”

    样例1：
    问题：安硕信息的股票代码是？
    回答：300380

    样例2：
    问题：该公司9月是否涨停？涨停次数为多少次？分别是哪几天？
    回答：涨停次数为2次，分别是2024年9月27日及2024年9月30日

    样例3：
    问题：涨停原因分别是？
    回答：2次涨停原因均为【金融科技+银行+华为+国产软件】

    样例4：
    问题：前十大股东中是否有投资基金参与？如果有的话，是哪家？
    回答：中国工商银行股份有限公司－大成中证360互联网+大数据100指数型证券投资基金
    """
    failure_count = 0  # 信息提取失败的计数器

    for question_team in questions:
        # 初始化该team的对话历史
        chat_history = []

        for convo in question_team['team']:
            chat_history.append({"role": "user", "content": convo['question']})

            sql = convo['related_tbl']
            sql_result = convo['sql_result']

            # 如果没有SQL结果，则直接回答“信息提取失败”
            if not sql_result:
                convo['answer'] = "信息提取失败"
                failure_count += 1  # 增加失败计数
            else:
                # 构建prompt，包括历史对话和所有相关的SQL语句
                sql_prompt = f"已知：回答问题所需要数据已通过{sql}会查询得到：{sql_result}" + sql2answer_prompt + "\n".join([chat['content'] for chat in chat_history])

                # 禁用 web_search 工具
                tools = [
                    {
                        "type": "web_search",
                        "web_search": {
                            "enable": False  # 禁用网络搜索
                        }
                    }
                ]
                response = client.chat.completions.create(
                    model="glm-4-flash",
                    messages=[
                        {"role": "system", "content": sql_prompt},
                        {"role": "user", "content": convo['question']}
                    ],
                    tools=tools
                )

                print(f"问题: {convo['question']}")
                print(f"响应: {response.choices[0].message.content}")

                chat_history.append({"role": "assistant", "content": response.choices[0].message.content})
                convo['answer'] = response.choices[0].message.content

    output_file_path = config['answer_file_path']
    with open(output_file_path, 'w', encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)

    print(f"处理完成，结果已保存到'sql2answer.json'文件中")
    print(f"信息提取失败的次数：{failure_count}")

