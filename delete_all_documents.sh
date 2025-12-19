#!/bin/bash
# 删除所有已上传的文档

# 默认配置
DEFAULT_PROJECT="safety"  # 默认项目：safety (隐患识别) 或 qa (知识问答)

# 使用方法
usage() {
    echo "使用方法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -p, --project <项目>  指定项目类型:"
    echo "                          safety  - 隐患识别 (默认，删除 rag-regulations + rag-hazard-db)"
    echo "                          qa      - RAG知识问答 (删除 rag-qa-knowledge)"
    echo "                          all     - 所有项目 (删除所有 collections)"
    echo "  -h, --help            显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0                      # 删除隐患识别项目文档（默认）"
    echo "  $0 -p qa                # 删除RAG知识问答项目文档"
    echo "  $0 -p all               # 删除所有项目文档"
    echo "  $0 --project safety     # 删除隐患识别项目文档"
    exit 1
}

# 解析参数
PROJECT="$DEFAULT_PROJECT"
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--project)
            PROJECT="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "❌ 错误: 未知参数 '$1'"
            usage
            ;;
    esac
done

# 验证项目类型
if [ "$PROJECT" != "safety" ] && [ "$PROJECT" != "qa" ] && [ "$PROJECT" != "all" ]; then
    echo "❌ 错误: 无效的项目类型 '$PROJECT'"
    echo "   支持的项目: safety, qa, all"
    echo ""
    usage
fi

# 根据项目类型设置 collections
if [ "$PROJECT" = "qa" ]; then
    COLLECTIONS=("rag-qa-knowledge")
    PROJECT_NAME="RAG知识问答"
elif [ "$PROJECT" = "all" ]; then
    COLLECTIONS=("rag-qa-knowledge" "rag-regulations" "rag-hazard-db")
    PROJECT_NAME="所有项目"
else
    COLLECTIONS=("rag-regulations" "rag-hazard-db")
    PROJECT_NAME="隐患识别"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "=== 删除文档 ==="
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🎯 目标项目: $PROJECT_NAME ($PROJECT)"
echo "📦 Collections: ${COLLECTIONS[*]}"
echo ""

# Qdrant 服务地址
QDRANT_URL="http://localhost:6333"

echo -e "\n正在查询所有 collections 的文档...\n"

total_deleted=0
total_before=0

for collection in "${COLLECTIONS[@]}"; do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "处理 Collection: $collection"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # 检查 collection 是否存在
    response=$(curl -s "$QDRANT_URL/collections/$collection" 2>/dev/null)
    collection_exists=$(echo "$response" | python3 -c "
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
        echo "  ⚠️  Collection 不存在，跳过"
        echo ""
        continue
    fi
    
    # 获取 collection 中的文档统计
    stats=$(curl -s "$QDRANT_URL/collections/$collection" 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    points = data['result']['points_count']
    print(f'{points}')
except:
    print('0')
" 2>/dev/null)
    
    echo "  📊 当前 chunks 数量: $stats"
    total_before=$((total_before + stats))
    
    if [ "$stats" -eq 0 ]; then
        echo "  ✓ Collection 已为空"
        echo ""
        continue
    fi
    
    # 获取所有唯一文件名
    echo "  🔍 正在扫描文档..."
    
    files=$(curl -s -X POST "$QDRANT_URL/collections/$collection/points/scroll" \
        -H "Content-Type: application/json" \
        -d '{"limit": 10000, "with_payload": true, "with_vector": false}' 2>/dev/null | python3 -c "
import sys, json
from collections import defaultdict

try:
    data = json.load(sys.stdin)
    points = data['result']['points']
    
    files = defaultdict(int)
    for p in points:
        filename = p['payload']['metadata']['filename']
        files[filename] += 1
    
    for filename, count in files.items():
        print(f'{filename}|{count}')
except Exception as e:
    pass
" 2>/dev/null)
    
    if [ -z "$files" ]; then
        echo "  ⚠️  无法获取文档列表"
        echo ""
        continue
    fi
    
    file_count=$(echo "$files" | wc -l)
    echo "  📁 找到 $file_count 个文档"
    echo ""
    
    # 逐个删除文档
    deleted_count=0
    failed_count=0
    
    while IFS='|' read -r filename chunks; do
        if [ -z "$filename" ]; then
            continue
        fi
        
        echo "  🗑️  删除: $filename (${chunks} chunks)"
        
        # 使用 Qdrant API 删除（通过 filename 过滤）
        response=$(curl -s -X POST "$QDRANT_URL/collections/$collection/points/delete" \
            -H "Content-Type: application/json" \
            -d "{
                \"filter\": {
                    \"must\": [
                        {
                            \"key\": \"metadata.filename\",
                            \"match\": {
                                \"value\": \"$filename\"
                            }
                        }
                    ]
                }
            }" 2>/dev/null)
        
        # 检查删除结果
        status=$(echo "$response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data.get('status') == 'ok':
        print('ok')
    else:
        print('error')
except:
    print('error')
" 2>/dev/null)
        
        if [ "$status" = "ok" ]; then
            echo "     ✓ 删除成功"
            ((deleted_count++))
        else
            echo "     ✗ 删除失败"
            ((failed_count++))
        fi
    done <<< "$files"
    
    echo ""
    echo "  📈 Collection 汇总:"
    echo "     成功删除: $deleted_count 个文档"
    if [ $failed_count -gt 0 ]; then
        echo "     失败: $failed_count 个文档"
    fi
    echo ""
    
    total_deleted=$((total_deleted + deleted_count))
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "=== 删除完成 ==="
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "删除前总 chunks: $total_before"
echo "成功删除文档数: $total_deleted"
echo ""

# 验证删除结果
echo "🔍 验证删除结果..."
echo ""

for collection in "${COLLECTIONS[@]}"; do
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
        continue
    fi
    
    stats=$(curl -s "$QDRANT_URL/collections/$collection" 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    result = data['result']
    print(f\"Collection: $collection\")
    print(f\"  Points: {result['points_count']}\")
    print(f\"  Indexed: {result['indexed_vectors_count']}\")
except:
    pass
" 2>/dev/null)
    
    echo "$stats"
done

echo ""
if [ "$PROJECT" = "all" ]; then
    echo "✅ 所有项目的文档已删除完成！"
else
    echo "✅ $PROJECT_NAME 项目的文档已删除完成！"
fi
