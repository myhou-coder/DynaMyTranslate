import en_markdown_to_zh
import os
import shutil
import nltk
from magic_pdf.data.data_reader_writer import FileBasedDataWriter
from magic_pdf.data.read_api import read_local_office  # 实际应为读取PDF的接口
from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
from magic_pdf.data.dataset import PymuDocDataset
from markdown_fixer import fix_markdown_after_translation


def pdf_to_markdown(pdf_path, output_dir="output"):
    # 初始化输出目录
    os.makedirs(os.path.join(output_dir, "images"), exist_ok=True)
    image_writer = FileBasedDataWriter(os.path.join(output_dir, "images"))
    md_writer = FileBasedDataWriter(output_dir)

    # 读取PDF文件
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    # 创建数据集实例
    ds = PymuDocDataset(pdf_bytes)  # [^6]

    # 执行分析流程
    infer_result = ds.apply(doc_analyze, ocr=False)  # [^2]
    pipe_result = infer_result.pipe_txt_mode(image_writer)  # [^2]

    # 生成Markdown
    name_without_ext = os.path.splitext(os.path.basename(pdf_path))[0]
    image_dir = os.path.basename(os.path.join(output_dir, "images"))
    pipe_result.dump_md(md_writer, f"{name_without_ext}.md", image_dir)  # [^1]


def translate_pdf_to_zh(pdf_path, output_dir, config_short, config_long, source_language="en", target_language="zh-CN"):
    """
    将PDF文件转换为Markdown并进行翻译。

    :param pdf_path: PDF文件的路径
    :param output_dir: 输出目录
    :param config_short: 短文本配置字典，包含API密钥等信息
    :param config_long: 长文本配置字典，包含API密钥等信息
    :param source_language: 原文语言
    :param target_language: 目标语言
    """
    # 提取PDF文件名（去除扩展名）
    name_without_suff = os.path.splitext(os.path.basename(pdf_path))[0]

    # 将PDF转换为Markdown
    pdf_to_markdown(pdf_path, output_dir=output_dir)

    # 获取生成的Markdown文件路径
    md_file_path = os.path.join(output_dir, f"{name_without_suff}.md")
    # 将Markdown文件从英文翻译为中文
    with open(md_file_path, "r", encoding="utf-8") as file:
        md_text = file.read()
    output_md = en_markdown_to_zh.main_workflow(md_text, config_short=config_short, config_long=config_long, source_language=source_language, target_language=target_language)

    # 保存翻译后的Markdown文件
    en_markdown_to_zh.save_markdown(output_md, md_file_path)

    # 修复Markdown标题层级
    try:
        api_key = config_short.get('api_key') or config_long.get('api_key')
        if api_key:
            print("🔧 开始修复Markdown标题层级...")
            fix_markdown_after_translation(output_dir, api_key)
        else:
            print("⚠️ 未找到API密钥，跳过标题修复")
    except Exception as e:
        print(f"⚠️ 标题修复失败，但翻译已完成: {str(e)}")

    print("翻译完成")



def translate_all_pdfs_in_folder(input_folder, output_folder, config_short, config_long, source_language="en", target_language="zh-CN"):
    # 确保输出文件夹存在
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    # 遍历输入文件夹中的所有文件
    for filename in os.listdir(input_folder):
        if filename.endswith(".pdf"):
            # 构造完整的文件路径
            pdf_path = os.path.join(input_folder, filename)

            # 创建以PDF文件名命名的子文件夹
            output_subdir = os.path.join(output_folder, os.path.splitext(filename)[0])
            if not os.path.exists(output_subdir):
                os.makedirs(output_subdir)
            # 将PDF文件复制到输出子文件夹中
            copied_pdf_path = os.path.join(output_subdir, filename)
            try:
                shutil.copy(pdf_path, copied_pdf_path)
            except FileNotFoundError as e:
                print(f"无法复制文件 {pdf_path} 到 {copied_pdf_path}: {e}")
                continue  # 跳过当前文件，继续处理下一个文件
            # 调用翻译函数
            translate_pdf_to_zh(pdf_path, output_subdir, config_short, config_long, source_language, target_language)

            # 删除原文PDF文件
            os.remove(pdf_path)

def translate_one_pdf(pdf_path, output_folder, config_short, config_long, source_language="en", target_language="zh-CN"):
    # 获取PDF文件名（不带扩展名）
    filename = os.path.basename(pdf_path)
    filename_without_ext = os.path.splitext(filename)[0]
    # 创建以PDF文件名命名的子文件夹
    output_subdir = os.path.join(output_folder, filename_without_ext)
    if not os.path.exists(output_subdir):
        os.makedirs(output_subdir)
    # 将PDF文件复制到输出子文件夹中
    copied_pdf_path = os.path.join(output_subdir, filename)
    try:
        shutil.copy(pdf_path, copied_pdf_path)
    except FileNotFoundError as e:
        print(f"无法复制文件 {pdf_path} 到 {copied_pdf_path}: {e}")
        return  # 如果复制失败，直接返回
    # 调用翻译函数
    translate_pdf_to_zh(pdf_path, output_subdir, config_short, config_long, source_language, target_language)
    # 将 output_subdir 压缩为 ZIP 文件
    zip_path = os.path.join(output_folder, filename_without_ext)
    shutil.make_archive(zip_path, 'zip', output_subdir)
    # 删除原始的 output_subdir 文件夹（可选）
    shutil.rmtree(output_subdir)
    



