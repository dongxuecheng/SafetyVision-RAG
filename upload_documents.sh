#!/bin/bash
# 批量上传指定文件夹下的所有文档

# 默认配置
API_URL="http://localhost:8080"
DEFAULT_DIR="/home/xcd/SafetyVision-RAG/file"

# 使用方法
usage() {
    echo "使用方法: $0 [文件夹路径]"
    echo ""
    echo "参数:"
    echo "  文件夹路径    要上传文档的文件夹路径（可选，默认: $DEFAULT_DIR）"
    echo ""
    echo "示例:"
    echo "  $0                          # 上传默认文件夹"
    echo "  $0 /path/to/documents       # 上传指定文件夹"
    echo ""
    echo "支持的文件类型: .pdf .docx .doc .xlsx .xls .md .markdown"
    exit 1
}

# 解析参数
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    usage
fi

DOC_DIR="${1:-$DEFAULT_DIR}"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "=== 批量上传文档 ==="
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📁 文档目录: $DOC_DIR"
echo "🌐 API 地址: $API_URL"
echo ""

# 检查目录是否存在
if [ ! -d "$DOC_DIR" ]; then
    echo "❌ 错误: 目录不存在: $DOC_DIR"
    echo ""
    usage
fi

# 检查并创建 Qdrant Collections
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤 1: 检查向量库 Collections"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

QDRANT_URL="http://localhost:6333"
COLLECTIONS=("rag-regulations" "rag-hazard-db")

for collection in "${COLLECTIONS[@]}"; do
    echo "📦 检查 Collection: $collection"
    
    # 检查 collection 是否存在
    response=$(curl -s "$QDRANT_URL/collections/$collection" 2>/dev/null)
    exists=$(echo "$response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if 'result' in data:
        print('yes')
    else:
        print('no')
except:
    print('no')
" 2>/dev/null)
    
    if [ "$exists" = "yes" ]; then
        echo "   ✅ 已存在"
    else
        echo "   ⚠️  不存在，正在创建..."
        
        # 创建 collection
        create_response=$(curl -s -X PUT "$QDRANT_URL/collections/$collection" \
            -H "Content-Type: application/json" \
            -d '{
                "vectors": {
                    "size": 1024,
                    "distance": "Cosine"
                }
            }' 2>/dev/null)
        
        # 检查创建结果
        create_status=$(echo "$create_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data.get('result') == True or 'result' in data:
        print('ok')
    else:
        print('error')
except:
    print('error')
" 2>/dev/null)
        
        if [ "$create_status" = "ok" ]; then
            echo "   ✅ 创建成功"
        else
            echo "   ❌ 创建失败"
            echo "   响应: $create_response"
            echo ""
            echo "❌ 无法创建必要的 Collections，请检查 Qdrant 服务"
            exit 1
        fi
    fi
done

echo ""

# 查找所有支持的文件
echo "🔍 正在扫描文档..."
files=$(find "$DOC_DIR" -type f \( \
    -iname "*.pdf" -o \
    -iname "*.docx" -o \
    -iname "*.doc" -o \
    -iname "*.xlsx" -o \
    -iname "*.xls" -o \
    -iname "*.md" -o \
    -iname "*.markdown" \
\) 2>/dev/null | sort)

if [ -z "$files" ]; then
    echo "⚠️  在目录中未找到支持的文档文件"
    echo ""
    exit 0
fi

total_count=$(echo "$files" | wc -l)
echo "📊 找到 $total_count 个文档"
echo ""

# 统计文件类型
echo "📑 文件类型分布:"
echo "$files" | sed 's/.*\.//' | sort | uniq -c | while read count ext; do
    printf "   %-10s: %3d 个\n" "$ext" "$count"
done
echo ""

# 询问是否继续
read -p "是否开始上传？(y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 取消上传"
    exit 0
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "开始上传..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 初始化计数器
uploaded=0
skipped=0
failed=0
current=0

# 按文件类型分组统计
declare -A type_success
declare -A type_failed
declare -A type_skipped

# 开始上传
while IFS= read -r file; do
    if [ -z "$file" ]; then
        continue
    fi
    
    ((current++))
    filename=$(basename "$file")
    filetype="${filename##*.}"
    
    echo "[$current/$total_count] 上传: $filename"
    
    # 判断文件类型并显示将要存储的 collection
    if [[ "$filetype" =~ ^(xlsx|xls|XLS|XLSX)$ ]]; then
        collection_type="hazard-db (Excel)"
    else
        collection_type="regulations (PDF/Word/Markdown)"
    fi
    echo "   📦 Collection: $collection_type"
    
    # 上传文件
    response=$(curl -s -X POST "$API_URL/api/documents/upload" \
        -F "files=@$file" \
        -F "skip_existing=true" \
        --max-time 120 2>&1)
    
    # 解析响应
    result=$(echo "$response" | python3 -c "
import sys, json

try:
    data = json.load(sys.stdin)
    if not data:
        print('error|0|Empty response')
        sys.exit(0)
    
    success = data.get('success', False)
    details = data.get('details', [])
    
    if details:
        detail = details[0]
        status = detail.get('status', 'unknown')
        chunks = detail.get('chunks', 0)
        msg = detail.get('message', '')
        print(f'{status}|{chunks}|{msg}')
    else:
        print('error|0|No details in response')
except json.JSONDecodeError as e:
    print(f'error|0|JSON parse error: {str(e)[:50]}')
except Exception as e:
    print(f'error|0|{str(e)[:50]}')
" 2>/dev/null)
    
    if [ -z "$result" ]; then
        echo "   ❌ 失败: 无响应或超时"
        echo "   原始响应: ${response:0:100}"
        ((failed++))
        ((type_failed[$filetype]++))
        echo ""
        continue
    fi
    
    IFS='|' read -r status chunks msg <<< "$result"
    
    case "$status" in
        "success")
            echo "   ✅ 成功 - $chunks chunks"
            ((uploaded++))
            ((type_success[$filetype]++))
            ;;
        "skipped")
            echo "   ⏭️  跳过 - $msg"
            ((skipped++))
            ((type_skipped[$filetype]++))
            ;;
        *)
            echo "   ❌ 失败 - $msg"
            ((failed++))
            ((type_failed[$filetype]++))
            ;;
    esac
    
    echo ""
    sleep 0.3  # 避免请求过快
done <<< "$files"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "=== 上传汇总 ==="
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 总体统计:"
echo "   总计: $total_count 个文档"
echo "   ✅ 成功: $uploaded"
echo "   ⏭️  跳过: $skipped"
if [ $failed -gt 0 ]; then
    echo "   ❌ 失败: $failed"
fi
echo ""

# 按文件类型显示统计
if [ ${#type_success[@]} -gt 0 ] || [ ${#type_failed[@]} -gt 0 ] || [ ${#type_skipped[@]} -gt 0 ]; then
    echo "📑 文件类型统计:"
    all_types=$(echo "$files" | sed 's/.*\.//' | sort -u)
    
    while IFS= read -r ext; do
        success_count=${type_success[$ext]:-0}
        failed_count=${type_failed[$ext]:-0}
        skipped_count=${type_skipped[$ext]:-0}
        total_type=$((success_count + failed_count + skipped_count))
        
        if [ $total_type -gt 0 ]; then
            printf "   %-10s: " "$ext"
            [ $success_count -gt 0 ] && printf "✅ %d  " $success_count
            [ $skipped_count -gt 0 ] && printf "⏭️  %d  " $skipped_count
            [ $failed_count -gt 0 ] && printf "❌ %d  " $failed_count
            echo ""
        fi
    done <<< "$all_types"
    echo ""
fi

# 等待并检查向量库状态
echo "⏳ 等待 3 秒后检查向量库状态..."
sleep 3
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "=== 向量库状态 ==="
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 检查两个 collection 的状态
QDRANT_URL="http://localhost:6333"
COLLECTIONS=("rag-regulations" "rag-hazard-db")

for collection in "${COLLECTIONS[@]}"; do
    # 检查 collection 是否存在
    collection_exists=$(curl -s "$QDRANT_URL/collections/$collection" 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if 'result' in data:
        print('yes')
    else:
        print('no')
except:
    print('no')
" 2>/dev/null)
    
    if [ "$collection_exists" != "yes" ]; then
        echo "📦 Collection: $collection"
        echo "   ⚠️  不存在"
        echo ""
        continue
    fi
    
    # 获取统计信息
    curl -s "$QDRANT_URL/collections/$collection" 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    result = data['result']
    print(f'📦 Collection: $collection')
    print(f'   Points: {result[\"points_count\"]}')
    print(f'   Indexed: {result[\"indexed_vectors_count\"]}')
    print()
except:
    pass
" 2>/dev/null
    
    # 获取文档类型分布
    curl -s -X POST "$QDRANT_URL/collections/$collection/points/scroll" \
        -H "Content-Type: application/json" \
        -d '{"limit": 5000, "with_payload": true, "with_vector": false}' 2>/dev/null | python3 -c "
from collections import defaultdict
import sys, json

try:
    data = json.load(sys.stdin)
    points = data['result']['points']
    
    types = defaultdict(int)
    for p in points:
        filename = p['payload']['metadata']['filename']
        ext = filename.split('.')[-1].lower()
        types[ext] += 1
    
    total = len(points)
    print('   文档类型分布:')
    for t, c in sorted(types.items(), key=lambda x: x[1], reverse=True):
        pct = c/total*100 if total > 0 else 0
        print(f'     {t}: {c} chunks ({pct:.1f}%)')
    print()
except:
    pass
" 2>/dev/null
done

echo "✅ 上传完成！"
echo ""
echo "💡 提示:"
echo "   - Excel 文件存储在 'rag-hazard-db' collection"
echo "   - 其他文件存储在 'rag-regulations' collection"
echo "   - 检索时会优先使用 regulations，必要时补充 hazard-db"
