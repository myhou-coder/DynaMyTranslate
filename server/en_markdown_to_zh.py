import os
from typing import Dict
import tiktoken
import nltk
import pre_process
import translate
import rebuild


def save_markdown(output_md: str, file_path: str) -> None:
    """
    将转化后的Markdown文本保存到指定文件路径。

    :param output_md: 转化后的Markdown文本
    :param file_path: 保存文件的路径
    """
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(output_md)


def main_workflow(input_md: str, config_short: Dict,config_long: Dict) -> str:
    """
    核心工作流函数，完成从输入Markdown文本到翻译后Markdown文本的完整流程。

    :param input_md: 输入的Markdown文本
    :param config: 配置参数，包含API提供者等信息
    """
    # 预处理阶段
    ast_blocks = pre_process.markdown_parser(input_md)
    split_blocks = []
    for block in ast_blocks:
        split_blocks.extend(pre_process.dynamic_splitter(block))

    # 翻译阶段
    client_short = translate.api_client_factory(config_short)
    client_long=translate.api_client_factory(config_long)
    # 判断领域
    front_text=[]
    num=0
    for idx, block in enumerate(split_blocks):
        if num>=6:
            break
        if block["type"]!='image':
            front_text.append(block["content"])
            num=num+1
    domain=client_short.detect_domain(front_text)

    translated = []
    for block in split_blocks:
        print("Sub Blocks:", block)
    for idx, block in enumerate(split_blocks):
        if block["type"]=='image':
            translated.append({**block, "content": block})
            continue
        content = block["content"]
        # 初始化tiktoken编码器
        encoder = tiktoken.get_encoding("cl100k_base")
        # 计算当前块的Token数
        tokens = encoder.encode(content)
        if len(tokens)<1000:
            print(block["content"])
            print("当前翻译模型：", config_short['modelname'], "\ntokens:", len(tokens))
            result = client_short.translate(block["content"],domain)
            print(result)
            translated.append({**block, "content": result})
        else:
            print(block["content"])
            print("当前翻译模型：", config_long['modelname'], "\ntokens:", len(tokens))
            result = client_long.translate(block["content"],domain)
            print(result)
            translated.append({**block, "content": result})


    # 后处理阶段
    output_md = rebuild.structure_rebuilder(translated)


    return output_md


