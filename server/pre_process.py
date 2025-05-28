import re
import tiktoken
import nltk
from typing import List, Dict, Union


# # # 下载NLTK的punkt资源（用于句子分割）
# nltk.download('punkt')
# nltk.download('punkt_tab')


def markdown_parser(text: str) -> List[Dict[str, Union[str, int]]]:
    """
    解析Markdown文本，生成AST树，并保留换行符号。

    :param text: 原始Markdown文本
    :return: 带层级结构的AST树
    """
    ast = []
    lines = text.split('\n')
    paragraph_buffer = []

    for line in lines:
        if line.strip() == "":
            continue

        # 识别标题
        heading_match = re.match(r'^(#+)\s+(.*)', line)
        if heading_match:
            # 如果段落缓冲区有内容，先将其作为一个段落block添加到AST中
            if paragraph_buffer:
                ast.append({"type": "paragraph", "content": "".join(paragraph_buffer)})
                paragraph_buffer = []
            # 添加标题block，并在内容后添加换行符
            level = len(heading_match.group(1))
            content = heading_match.group(2)
            ast.append({"type": "heading", "level": level, "content": content})
            continue

        # 识别图片
        image_match = re.match(r'!\[(.*?)\]\((.*?)\)', line)
        if image_match:
            # 如果段落缓冲区有内容，先将其作为一个段落block添加到AST中
            if paragraph_buffer:
                ast.append({"type": "paragraph", "content": "".join(paragraph_buffer)})
                paragraph_buffer = []
            # 添加图片block，并在内容后添加换行符
            alt_text = image_match.group(1)
            path = image_match.group(2)
            ast.append({"type": "image", "alt": alt_text, "path": path})
            continue

        # 如果不是标题或图片，则将其视为段落的一部分
        paragraph_buffer.append(line.strip())
        paragraph_buffer.append("\n")

    # 处理最后可能剩余的段落
    if paragraph_buffer:
        ast.append({"type": "paragraph", "content": "".join(paragraph_buffer) })

    return ast


def dynamic_splitter(block: Dict[str, Union[str, int]], max_tokens: int = 8192) -> List[Dict[str, Union[str, int]]]:
    """
    动态拆分文本块，确保每个子块的Token数不超过最大限制。

    :param block: 单个文本块
    :param max_tokens: 最大Token数限制
    :return: 拆分后的子块列表
    """
    content = block.get("content", "")
    if not content:
        return [block]
    # 初始化tiktoken编码器
    encoder = tiktoken.get_encoding("cl100k_base")
    # 计算当前块的Token数
    tokens = encoder.encode(content)
    if len(tokens) <= max_tokens:
        return [block]

    # 按换行符拆分
    paragraphs = content.split('\n')
    sub_blocks = []
    current_block = {"type": block["type"], "content": ""}
    current_tokens = 0

    for paragraph in paragraphs:
        paragraph_tokens = encoder.encode(paragraph)

        # 如果当前段落加上已有的Token数超过限制，则创建新的子块
        if current_tokens + len(paragraph_tokens) > max_tokens:
            if current_block["content"]:
                sub_blocks.append(current_block)
            current_block = {"type": block["type"], "content": paragraph}
            current_tokens = len(paragraph_tokens)
        else:
            current_block["content"] += '\n' + paragraph if current_block["content"] else paragraph
            current_tokens += len(paragraph_tokens)

    if current_block["content"]:
        sub_blocks.append(current_block)

    # 如果按换行符拆分后仍超限，则按句子拆分
    if len(sub_blocks) == 1 and len(encoder.encode(sub_blocks[0]["content"])) > max_tokens:
        sentences = nltk.sent_tokenize(sub_blocks[0]["content"])
        sub_blocks = []
        current_block = {"type": block["type"], "content": ""}
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = encoder.encode(sentence)

            if current_tokens + len(sentence_tokens) > max_tokens:
                if current_block["content"]:
                    sub_blocks.append(current_block)
                current_block = {"type": block["type"], "content": sentence}
                current_tokens = len(sentence_tokens)
            else:
                current_block["content"] += ' ' + sentence if current_block["content"] else sentence
                current_tokens += len(sentence_tokens)

        if current_block["content"]:
            sub_blocks.append(current_block)

    # 为子块添加连续标识符
    for i, sub_block in enumerate(sub_blocks):
        sub_block["identifier"] = f"{block.get('identifier', 'block')}-{i + 1}"

    return sub_blocks

