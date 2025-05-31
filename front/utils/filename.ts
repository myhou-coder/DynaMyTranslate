/**
 * 文件名处理工具函数
 */

// 文件名最大长度配置
const MAX_FILENAME_LENGTH = 100; // 最大文件名长度（包含扩展名）
const MAX_BASENAME_LENGTH = 80;  // 最大基础文件名长度（不包含扩展名）

/**
 * 截断文件名到指定长度
 * @param filename 原始文件名
 * @param maxLength 最大长度（可选，默认使用配置值）
 * @returns 截断后的文件名
 */
export function truncateFilename(filename: string, maxLength = MAX_FILENAME_LENGTH): string {
  if (filename.length <= maxLength) {
    return filename;
  }

  // 分离文件名和扩展名
  const lastDotIndex = filename.lastIndexOf('.');
  const extension = lastDotIndex !== -1 ? filename.substring(lastDotIndex) : '';
  const basename = lastDotIndex !== -1 ? filename.substring(0, lastDotIndex) : filename;

  // 计算基础文件名可用的最大长度
  const maxBasenameLength = Math.min(
    maxLength - extension.length,
    MAX_BASENAME_LENGTH
  );

  if (maxBasenameLength <= 0) {
    // 如果扩展名太长，就保留最基本的部分
    return `file${extension}`;
  }

  // 截断基础文件名，保留有意义的部分
  let truncatedBasename = basename.substring(0, maxBasenameLength);

  // 去除可能的尾部空格或特殊字符
  truncatedBasename = truncatedBasename.trim();

  // 如果截断后的文件名太短，添加一些标识
  if (truncatedBasename.length < 3) {
    truncatedBasename = `file_${Date.now().toString().slice(-6)}`;
  }

  return `${truncatedBasename}${extension}`;
}

/**
 * 验证文件名是否过长
 * @param filename 文件名
 * @param maxLength 最大长度
 * @returns 是否过长
 */
export function isFilenameTooLong(filename: string, maxLength = MAX_FILENAME_LENGTH): boolean {
  return filename.length > maxLength;
}

/**
 * 生成安全的文件名（移除或替换特殊字符）
 * @param filename 原始文件名
 * @returns 安全的文件名
 */
export function sanitizeFilename(filename: string): string {
  // 移除或替换可能引起问题的字符
  return filename
    .replace(/[<>:"/\\|?*]/g, '_') // 替换Windows不允许的字符
    .replace(/[\x00-\x1f\x80-\x9f]/g, '') // 移除控制字符
    .replace(/^\.+/, '') // 移除开头的点
    .replace(/\.+$/, '') // 移除结尾的点（扩展名除外）
    .replace(/\s+/g, '_') // 替换空格为下划线
    .trim();
}

/**
 * 完整的文件名处理：清理、截断
 * @param filename 原始文件名
 * @param maxLength 最大长度
 * @returns 处理后的文件名
 */
export function processFilename(filename: string, maxLength = MAX_FILENAME_LENGTH): string {
  // 首先清理文件名
  let processedName = sanitizeFilename(filename);
  
  // 然后截断到合适长度
  processedName = truncateFilename(processedName, maxLength);
  
  return processedName;
}

/**
 * 为重复文件名添加时间戳
 * @param filename 文件名
 * @returns 带时间戳的文件名
 */
export function addTimestampToFilename(filename: string): string {
  const timestamp = Date.now().toString().slice(-6); // 使用时间戳的后6位
  const lastDotIndex = filename.lastIndexOf('.');
  
  if (lastDotIndex !== -1) {
    const basename = filename.substring(0, lastDotIndex);
    const extension = filename.substring(lastDotIndex);
    return `${basename}_${timestamp}${extension}`;
  } else {
    return `${filename}_${timestamp}`;
  }
} 