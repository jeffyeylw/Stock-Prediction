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
    
    def parse_hunk_header(self, header):
        """解析 diff hunk 头部"""
        match = re.match(r'@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@', header)
        if match:
            return int(match.group(1))
        return None

    def calculate_position(self, patch, target_line):
        """
        计算评论在 diff 中的实际位置
        patch: diff 内容
        target_line: 目标行号
        返回: 相对于 hunk 开始的位置
        """
        if not patch:
            return None
        
        lines = patch.split('\n')
        position = 0
        current_line = 0
        is_in_hunk = False
        
        for i, line in enumerate(lines):
            if line.startswith('@@'):
                is_in_hunk = True
                current_line = self.parse_hunk_header(line)
                if current_line is None:
                    return None
                current_line -= 1  # 调整起始行号
                continue
            
            if not is_in_hunk:
                continue
                
            position += 1
            
            if line.startswith('-'):
                continue
            elif line.startswith('+'):
                current_line += 1
            elif not line.startswith('\\'):  # 忽略 'No newline at end of file'
                current_line += 1
                
            if current_line == target_line:
                return position
                
        return None

    def get_review_prompt(self, code_diff):
        return f"""作为一个专业的代码审查员，请仔细检查以下代码差异并提供改进建议。
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
                    3. 确保行号对应代码差异中的实际行号
                    4. 返回的必须是合法的JSON格式
                    """

    def analyze_code(self, diff_content):
        response = self.client.chat.completions.create(
            model="glm-4-flash",
            messages=[
                {"role": "system", "content": "你是一个经验丰富的代码审查专家。"},
                {"role": "user", "content": self.get_review_prompt(diff_content)}
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
                review_result = self.analyze_code(file.patch)
                for comment in review_result.get('comments', []):
                    position = self.calculate_position(file.patch, comment['line_number'])
                    if position is not None:
                        all_review_comments.append({
                            'path': file.filename,
                            'position': position,
                            'body': comment['comment']
                        })
                    else:
                        print(f"Could not determine position for line {comment['line_number']} in {file.filename}")
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
