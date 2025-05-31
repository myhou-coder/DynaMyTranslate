import os
import re
import time
from typing import List, Tuple
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_deepseek import ChatDeepSeek

class MarkdownFixer:
    def __init__(self, api_key: str):
        self.llm = ChatDeepSeek(
            api_key=api_key,
            model="deepseek-chat",
            temperature=0.1,
            max_tokens=8192,
            max_retries=3,
            timeout=60
        )
        self.prompt = ChatPromptTemplate.from_template(
            """请根据学术论文结构规范修复以下标题层级：
要求：
1. 仅调整标题层级（#的数量）
2. 保持标题文本内容不变
3. 确保层级结构合理（# 一级标题，## 二级标题）
4. 返回修正后的完整标题列表

原始标题结构：
{headings}

请直接返回修正后的标题列表："""
        )
        self.chain = self.prompt | self.llm | StrOutputParser()
    
    def _extract_headings(self, content: str) -> Tuple[List[str], str]:
        """提取标题并保留锚点"""
        headings = []
        body = []
        for line in content.split('\n'):
            if line.startswith('#'):
                headings.append(line)
                body.append(f"__HEADING_PLACEHOLDER_{len(headings)}__")
            else:
                body.append(line)
        return headings, '\n'.join(body)
    
    def _rebuild_content(self, body: str, new_headings: List[str]) -> str:
        """重建Markdown内容"""
        content_lines = []
        heading_idx = 0
        for line in body.split('\n'):
            if line.startswith('__HEADING_PLACEHOLDER_'):
                if heading_idx < len(new_headings):
                    content_lines.append(new_headings[heading_idx])
                    heading_idx += 1
            else:
                content_lines.append(line)
        return '\n'.join(content_lines)
    
    def fix_markdown_file(self, md_path: str, max_retries: int = 3) -> bool:
        """修复单个Markdown文件的标题结构
        
        Args:
            md_path: Markdown文件路径
            max_retries: 最大重试次数
            
        Returns:
            bool: 修复是否成功
        """
        if not os.path.exists(md_path):
            print(f"❌ 文件不存在：{md_path}")
            return False
            
        try:
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取标题
            original_headings, body = self._extract_headings(content)
            
            # 如果没有标题，直接返回成功
            if not original_headings:
                print(f"ℹ️ 文件无标题，跳过修复：{os.path.basename(md_path)}")
                return True
            
            for attempt in range(max_retries):
                try:
                    # 调用LLM修复
                    fixed_headings = self.chain.invoke({
                        "headings": '\n'.join(original_headings)
                    })
                    
                    # 解析响应
                    new_headings = [h.strip() for h in fixed_headings.split('\n') if h.strip().startswith('#')]
                    if len(new_headings) != len(original_headings):
                        raise ValueError("标题数量不匹配")
                    
                    # 重建内容
                    fixed_content = self._rebuild_content(body, new_headings)
                    
                    # 原子写入
                    tmp_path = f"{md_path}.tmp"
                    with open(tmp_path, 'w', encoding='utf-8') as f:
                        f.write(fixed_content)
                    os.replace(tmp_path, md_path)
                    
                    print(f"✅ 标题修复完成：{os.path.basename(md_path)}")
                    return True
                    
                except Exception as e:
                    if attempt == max_retries - 1:
                        print(f"❌ 修复失败《{os.path.basename(md_path)}》: {str(e)}")
                    time.sleep(2 ** attempt)
                    
        except Exception as e:
            print(f"❌ 文件操作失败《{os.path.basename(md_path)}》: {str(e)}")
            
        return False

    def fix_markdown_in_directory(self, directory_path: str) -> int:
        """修复目录中所有Markdown文件的标题结构
        
        Args:
            directory_path: 目录路径
            
        Returns:
            int: 成功修复的文件数量
        """
        if not os.path.exists(directory_path):
            print(f"❌ 目录不存在：{directory_path}")
            return 0
        
        fixed_count = 0
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                if file.endswith('.md'):
                    md_path = os.path.join(root, file)
                    if self.fix_markdown_file(md_path):
                        fixed_count += 1
        
        return fixed_count

def fix_markdown_after_translation(output_dir: str, api_key: str) -> bool:
    """在翻译完成后修复Markdown文件的标题层级
    
    Args:
        output_dir: 输出目录路径
        api_key: DeepSeek API密钥
        
    Returns:
        bool: 修复是否成功
    """
    try:
        fixer = MarkdownFixer(api_key)
        fixed_count = fixer.fix_markdown_in_directory(output_dir)
        print(f"🔧 共修复了 {fixed_count} 个Markdown文件的标题层级")
        return True
    except Exception as e:
        print(f"❌ 标题修复过程出错: {str(e)}")
        return False

# 保留原有的兼容代码，但标记为已弃用
def fix_markdown(article, max_retries: int = 3) -> None:
    """已弃用：修复单个Markdown文件的标题结构（保持向后兼容）"""
    print("⚠️ fix_markdown 函数已弃用，请使用 fix_markdown_file")
    if hasattr(article, 'pdf_parsing_result_path') and article.pdf_parsing_result_path:
        # 这里需要API密钥，但旧接口没有提供，所以抛出异常
        raise ValueError("需要API密钥，请使用新的 fix_markdown_file 方法")

if __name__ == "__main__":
    # 测试代码
    test_dir = "test_output"
    test_api_key = "your-api-key-here"
    
    if os.path.exists(test_dir):
        success = fix_markdown_after_translation(test_dir, test_api_key)
        print(f"修复结果: {'成功' if success else '失败'}")
    else:
        print(f"测试目录不存在: {test_dir}")