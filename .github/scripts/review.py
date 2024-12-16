import os
import json
from github import Github
import zhipuai
from dotenv import load_dotenv

class CodeReviewer:
    def __init__(self):
        # 加载环境变量
        load_dotenv()
        
        self.gh = Github(os.getenv('GITHUB_TOKEN'))
        zhipuai.api_key = os.getenv('ZHIPU_API_KEY')
        self.repo_name = os.getenv('GITHUB_REPOSITORY')
        self.repo = self.gh.get_repo(self.repo_name)

    def get_review_prompt(self, code_diff):
        return f"""作为一个专业的代码审查员，请仔细检查以下代码差异并提供不超过3个最重要的改进建议。
代码差异:
{code_diff}

请用以下JSON格式返回你的评审意见:
{{
    "comments": [
        {{
            "line_number": <行号>,
            "comment": "<具体的改进建议，包括原因和建议的改进方式>"
        }},
        ...
    ]
}}
注意:
1. 只关注最重要的问题
2. 评论要具体且有建设性
3. 每个文件最多提供3条评论
4. 确保行号对应代码差异中的实际行号
5. 返回的必须是合法的JSON格式
"""

    def analyze_code(self, diff_content):
        response = zhipuai.model.chat.completions.create(
            model="glm-4-flash",  # 使用 glm-4-flash 模型
            messages=[
                {"role": "system", "content": "你是一个经验丰富的代码审查专家。"},
                {"role": "user", "content": self.get_review_prompt(diff_content)}
            ],
            temperature=0.3,  # 降低温度以获得更加确定性的输出
            top_p=0.85,
            stream=False
        )
        
        try:
            # 解析返回的内容
            content = response.choices[0].message.content
            return json.loads(content)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {str(e)}")
            print(f"Raw response: {content}")
            return {"comments": []}
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return {"comments": []}

    def review_pr(self):
        # 获取PR编号
        pr_number = int(os.getenv('GITHUB_EVENT_NUMBER', 0))
        if pr_number == 0:
            with open(os.getenv('GITHUB_EVENT_PATH')) as f:
                event_data = json.load(f)
                pr_number = event_data['pull_request']['number']

        pr = self.repo.get_pull(pr_number)
        files = pr.get_files()

        for file in files:
            if not self._should_review_file(file.filename):
                continue

            try:
                review_result = self.analyze_code(file.patch)
                self._submit_comments(pr, file, review_result.get('comments', []))
            except Exception as e:
                print(f"Error reviewing file {file.filename}: {str(e)}")

    def _should_review_file(self, filename):
        # 可以根据需要添加文件过滤规则
        ignore_extensions = ['.md', '.txt', '.json', '.yaml', '.yml']
        return not any(filename.endswith(ext) for ext in ignore_extensions)

    def _submit_comments(self, pr, file, comments):
        for comment in comments[:3]:  # 限制每个文件最多3条评论
            try:
                line_number = comment['line_number']
                comment_body = comment['comment']
                
                # 创建行级评论
                pr.create_review_comment(
                    body=comment_body,
                    commit_id=file.sha,
                    path=file.filename,
                    line=line_number
                )
                print(f"Successfully added comment to line {line_number} in {file.filename}")
            except Exception as e:
                print(f"Error submitting comment: {str(e)}")

def main():
    reviewer = CodeReviewer()
    reviewer.review_pr()

if __name__ == "__main__":
    main()