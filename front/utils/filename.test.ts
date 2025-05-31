/**
 * 文件名处理功能测试
 */

import { 
  truncateFilename, 
  isFilenameTooLong, 
  sanitizeFilename, 
  processFilename, 
  addTimestampToFilename 
} from './filename'

// 测试数据
const testCases = [
  {
    name: '正常长度文件名',
    input: 'normal_file.pdf',
    expected: 'normal_file.pdf'
  },
  {
    name: '超长文件名',
    input: 'this_is_a_very_very_very_very_very_very_very_very_very_very_long_filename_that_should_be_truncated.pdf',
    shouldBeTruncated: true
  },
  {
    name: '包含特殊字符',
    input: 'file<>:"/\\|?*name.pdf',
    shouldBeSanitized: true
  },
  {
    name: '包含中文字符',
    input: '中文文件名测试_这是一个很长的中文文件名_包含各种字符.pdf',
    shouldHandle: true
  },
  {
    name: '无扩展名',
    input: 'filename_without_extension',
    expected: 'filename_without_extension'
  }
]

// 运行测试的函数
export function runFilenameTests() {
  console.log('🧪 开始文件名处理功能测试...')
  
  testCases.forEach((testCase, index) => {
    console.log(`\n📝 测试 ${index + 1}: ${testCase.name}`)
    console.log(`输入: "${testCase.input}"`)
    
    // 测试长度检查
    const isTooLong = isFilenameTooLong(testCase.input)
    console.log(`是否过长: ${isTooLong}`)
    
    // 测试清理功能
    const sanitized = sanitizeFilename(testCase.input)
    console.log(`清理后: "${sanitized}"`)
    
    // 测试截断功能
    const truncated = truncateFilename(testCase.input)
    console.log(`截断后: "${truncated}"`)
    
    // 测试完整处理
    const processed = processFilename(testCase.input)
    console.log(`完整处理: "${processed}"`)
    
    // 验证结果
    if (testCase.expected && processed !== testCase.expected) {
      console.log(`⚠️ 预期: "${testCase.expected}", 实际: "${processed}"`)
    }
    
    if (testCase.shouldBeTruncated && processed.length >= testCase.input.length) {
      console.log(`⚠️ 文件名应该被截断但没有被截断`)
    }
    
    if (testCase.shouldBeSanitized && processed === testCase.input) {
      console.log(`⚠️ 文件名应该被清理但没有被清理`)
    }
    
    // 检查处理后的文件名长度
    if (processed.length > 100) {
      console.log(`❌ 处理后的文件名仍然过长: ${processed.length} 字符`)
    } else {
      console.log(`✅ 处理后的文件名长度合适: ${processed.length} 字符`)
    }
  })
  
  // 额外测试
  console.log('\n🔄 额外功能测试:')
  
  // 测试时间戳添加
  const withTimestamp = addTimestampToFilename('test.pdf')
  console.log(`添加时间戳: "${withTimestamp}"`)
  
  // 测试边界情况
  const emptyName = processFilename('')
  console.log(`空文件名处理: "${emptyName}"`)
  
  const onlyExtension = processFilename('.pdf')
  console.log(`只有扩展名处理: "${onlyExtension}"`)
  
  console.log('\n🎉 文件名处理功能测试完成!')
}

// 如果直接运行此文件，执行测试
if (typeof window !== 'undefined') {
  // 在浏览器环境中，可以通过控制台运行测试
  (window as any).runFilenameTests = runFilenameTests
  console.log('💡 在浏览器控制台中运行 runFilenameTests() 来执行测试')
} 