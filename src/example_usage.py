"""
测试多格式文档处理示例

演示如何使用新的文档处理功能
"""

from datetime import datetime

# 处理不同格式的文档
print("=" * 60)
print("多格式文档处理测试")
print("=" * 60)

# 1. PDF 处理示例
print("\n1. PDF处理 - 传统Chunking策略")
print("   - 使用 RecursiveCharacterTextSplitter")
print("   - chunk_size=1000, chunk_overlap=200")
print("   - 适合长文本文档，保持语义连贯性")

# 2. Word 处理示例
print("\n2. Word处理 - 传统Chunking策略")
print("   - 提取所有段落文本")
print("   - 使用 RecursiveCharacterTextSplitter")
print("   - 支持 .doc 和 .docx 格式")

# 3. Excel 处理示例 (关键!)
print("\n3. Excel处理 - Row-to-Text策略 ⭐")
print("   - 第一行作为表头")
print("   - 每行数据结合表头转换为语义文本")
print("\n   示例转换:")
print("   表格数据:")
print("   | 姓名 | 职位 | 部门   |")
print("   | 张三 | 经理 | 销售部 |")
print("   | 李四 | 员工 | 技术部 |")
print("\n   转换为:")
print("   '第2行数据：姓名为张三，职位为经理，部门为销售部。'")
print("   '第3行数据：姓名为李四，职位为员工，部门为技术部。'")
print("\n   优势:")
print("   ✓ 保留结构信息")
print("   ✓ 支持自然语言查询: '经理是谁？' -> 能找到张三")
print("   ✓ 语义完整，易于向量检索")

# 支持的格式
print("\n" + "=" * 60)
print("支持的文档格式:")
print("=" * 60)
print("  - PDF:  .pdf")
print("  - Word: .doc, .docx")
print("  - Excel: .xls, .xlsx")

# API 使用示例
print("\n" + "=" * 60)
print("API 使用示例:")
print("=" * 60)
api_example = """
# 上传文档
curl -X POST "http://localhost:8000/api/documents/upload" \\
  -F "files=@员工信息.xlsx" \\
  -F "files=@规章制度.pdf" \\
  -F "files=@安全手册.docx"

# 查询文档
curl "http://localhost:8000/api/documents"

# 分析图片（使用RAG）
curl -X POST "http://localhost:8000/analyze_image" \\
  -F "file=@workplace.jpg"
"""
print(api_example)

print("\n" + "=" * 60)
print("代码特点:")
print("=" * 60)
print("  ✓ 简洁: 使用工厂模式统一处理")
print("  ✓ 可扩展: 易于添加新格式支持")
print("  ✓ 符合最新标准: 使用 Python 3.10+ 特性")
print("  ✓ 类型安全: 完整的类型注解")
