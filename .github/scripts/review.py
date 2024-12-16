import os
import json
import re
from github import Github
from zhipuai import ZhipuAI
from dotenv import load_dotenv

class CodeReviewer:
    def __init__(self):
        load_dotenv()
        
        self.gh = Github(os.getenv('GITHUB_TOKEN'))
        self.api_key = os.getenv('ZHIPU_API_KEY')
        self.client = ZhipuAI(api_key=self.api_key)
        self.repo_name = os.getenv('GITHUB_REPOSITORY')
        if not self.repo_name:
            raise ValueError("GITHUB_REPOSITORY environment variable is not set.")
        self.repo = self.gh.get_repo(self.repo_name)

    def extract_added_lines(self, patch):
        """
        从patch中提取新增的代码行及其行号
        返回: [(行号, 代码行, position)]
        """
        if not patch:
            return []

        lines = patch.split('\n')
        added_lines = []
        current_line = 0
        position = 0
        
        for line in lines:
            position += 1
            
            if line.startswith('@@'):
                # 提取hunk的起始行号
                match = re.match(r'@@ -\d+(?:,\d+)? \+(\d+)', line)
                if match:
                    current_line = int(match.group(1)) - 1
                continue
                
            if line.startswith('+') and not line.startswith('+++'): 
                current_line += 1
                code_line = line[1:]  # 去掉'+'前缀
                added_lines.append((current_line, code_line, position))
            elif not line.startswith('-') and not line.startswith('\\'): 
                current_line += 1

        return added_lines

    def get_review_prompt(self, added_lines):
        code_text = '\n'.join([f"行{line[0]}: {line[1]}" for line in added_lines])
        return f"""作为一个专业的代码审查员，请仔细检查以下新增的代码行并提供改进建议。
                    新增代码:
                    {code_text}

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
                    3. 只评论新增的代码行
                    4. 返回的必须是合法的JSON格式
                    """

    def analyze_code(self, added_lines):
        if not added_lines:
            return {"comments": []}
            
        response = self.client.chat.completions.create(
            model="glm-4-flash",
            messages=[
                {"role": "system", "content": "你是一个经验丰富的代码审查专家。"},
                {"role": "user", "content": self.get_review_prompt(added_lines)}
            ],
            temperature=0.3,
            top_p=0.85,
            stream=False
        )
        
        try:
            content = response.choices[0].message.content.strip()
            if content.startswith('```json'):
                content = content[len('```json'):].strip()
            if content.endswith('```'):
                content = content[:-len('```')].strip()
            return json.loads(content)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {str(e)}")
            print(f"Raw response: {content}")
            return {"comments": []}
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return {"comments": []}

    def review_pr(self):
        pr_number = int(os.getenv('GITHUB_EVENT_NUMBER', 0))
        if pr_number == 0:
            with open(os.getenv('GITHUB_EVENT_PATH')) as f:
                event_data = json.load(f)
                pr_number = event_data['pull_request']['number']

        pr = self.repo.get_pull(pr_number)
        files = pr.get_files()
        all_review_comments = []
        
        for file in files:
            if not self._should_review_file(file.filename):
                continue

            try:
                # 提取新增的代码行
                added_lines = self.extract_added_lines(file.patch)
                if not added_lines:
                    continue

                # 创建行号到position的映射
                line_to_position = {line[0]: line[2] for line in added_lines}
                
                # 分析代码并获取评论
                review_result = self.analyze_code(added_lines)
                
                for comment in review_result.get('comments', []):
                    line_number = comment['line_number']
                    if line_number in line_to_position:
                        all_review_comments.append({
                            'path': file.filename,
                            'position': line_to_position[line_number],
                            'body': comment['comment']
                        })
            except Exception as e:
                print(f"Error reviewing file {file.filename}: {str(e)}")
        
        # 只取总共最重要的3条评论
        review_comments = all_review_comments[:3]
        
        if review_comments:
            try:
                # 创建评审
                review = pr.create_review(
                    body="Code review comments",
                    event='COMMENT',
                    comments=review_comments
                )
                print(f"Successfully added {len(review_comments)} comments to the pull request")
            except Exception as e:
                print(f"Error submitting review: {str(e)}")
                print("Review comments data:")
                print(json.dumps(review_comments, indent=2))

    def _should_review_file(self, filename):
        ignore_extensions = ['.md', '.txt', '.json', '.yaml', '.yml']
        return not any(filename.endswith(ext) for ext in ignore_extensions)

def main():
    reviewer = CodeReviewer()
    reviewer.review_pr()

if __name__ == "__main__":
    main()
