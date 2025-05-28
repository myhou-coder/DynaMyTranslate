import re
from typing import List, Dict


def structure_rebuilder(blocks: List[Dict]) -> str:
    """
    重建Markdown文本结构。

    :param blocks: 翻译后的块列表
    :return: 重建后的Markdown文本
    """
    md_text = []
    for block in blocks:
        if block["type"] == "heading":
            # 标题添加换行符
            level = block.get("level", 1)
            content = block["content"]
            md_text.append(f"{'#' * level} {content}\n")
        elif block["type"] == "paragraph":
            # 段落直接拼接
            md_text.append(f"{block['content']}\n")
        elif block["type"] == "image":
            # 图片路径UTF-8编码验证
            alt = block.get("alt", "")
            path = block["path"]
            try:
                path.encode('utf-8')
                md_text.append(f"![{alt}]({path})\n")
            except UnicodeEncodeError:
                md_text.append(f"![{alt}](<{path}>)\n")

    # 格式美化
    md_text = "".join(md_text)
    # 统一中英文间距
    md_text = re.sub(r'([\u4e00-\u9fff])([a-zA-Z])', r'\1 \2', md_text)
    md_text = re.sub(r'([a-zA-Z])([\u4e00-\u9fff])', r'\1 \2', md_text)
    # 删除多余空行
    md_text = re.sub(r'\n{3,}', '\n\n', md_text)

    return md_text.strip()



