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

    def find_line_in_hunks(self, patch, target_line):
        """
        在patch的所有hunks中查找目标行并返回正确的position
        """
        if not patch:
            return None

        hunks = patch.split('\n@@')[1:]  # 分割所有的hunks
        position = 0  # 整体position计数器
        
        for hunk in hunks:
            if not hunk.strip():
                continue
                
            hunk_lines = hunk.split('\n')
            # 解析hunk头部
            header = hunk_lines[0]
            match = re.match(r'\s*-\d+(?:,\d+)?\s+\+(\d+)(?:,\d+)?\s*@@', header)
            if not match:
                continue
                
            current_line = int(match.group(1))
            position += 1  # 为hunk头部增加position计数
            
            for line in hunk_lines[1:]:
                if line.startswith('+'):
                    if current_line == target_line:
                        return position
                    current_line += 1
                elif line.startswith('-'):
                    pass  # 删除的行不影响当前行号
                elif not line.startswith('\\'):  # 忽略 'No newline' 标记
                    current_line += 1
                    
                position += 1
                
        return None

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
                    4. 确保行号对应代码差异中的新添加或修改的行
                    5. 返回的必须是合法的JSON格式
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
        review_comments = []
        
        for file in files:
            if not self._should_review_file(file.filename):
                continue

            try:
                review_result = self.analyze_code(file.patch)
                for comment in review_result.get('comments', [])[:3]:
                    position = self.find_line_in_hunks(file.patch, comment['line_number'])
                    if position is not None:
                        review_comments.append({
                            'path': file.filename,
                            'position': position,
                            'body': comment['comment']
                        })
                    else:
                        print(f"Could not determine position for line {comment['line_number']} in {file.filename}")
                        # 打印完整的patch内容以便调试
                        print(f"Complete patch for {file.filename}:")
                        print(file.patch)
            except Exception as e:
                print(f"Error reviewing file {file.filename}: {str(e)}")
        
        if review_comments:
            try:
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
