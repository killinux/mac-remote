#!/bin/bash
# 压缩图片到 Claude 可读大小（<5MB, 长边≤4096px）
# 用法: compress_img.sh <图片路径> [输出目录]
# 保留原图，压缩后文件名加 _compressed 后缀
set -eu

if [ $# -lt 1 ]; then
    echo "用法: $0 <图片路径> [输出目录]"
    echo "示例: $0 ~/Desktop/screenshot.png"
    echo "      $0 ~/Desktop/photo.jpg /tmp"
    exit 1
fi

INPUT="$1"
if [ ! -f "$INPUT" ]; then
    echo "错误: 文件不存在: $INPUT"
    exit 1
fi

OUTDIR="${2:-$(dirname "$INPUT")}"
BASENAME="$(basename "$INPUT")"
NAME="${BASENAME%.*}"
EXT="${BASENAME##*.}"
OUTPUT="$OUTDIR/${NAME}_compressed.jpg"

MAX_SIZE=4800000  # 4.8MB target (leave margin for 5MB limit)
MAX_DIM=4096

# Get original info
ORIG_SIZE=$(stat -f%z "$INPUT")
ORIG_W=$(sips -g pixelWidth "$INPUT" | tail -1 | awk '{print $2}')
ORIG_H=$(sips -g pixelHeight "$INPUT" | tail -1 | awk '{print $2}')
ORIG_MB=$(echo "scale=1; $ORIG_SIZE / 1048576" | bc)

echo "原图: ${ORIG_W}x${ORIG_H}, ${ORIG_MB}MB ($INPUT)"

# If already small enough, just copy
if [ "$ORIG_SIZE" -le "$MAX_SIZE" ] && [ "$ORIG_W" -le "$MAX_DIM" ] && [ "$ORIG_H" -le "$MAX_DIM" ]; then
    cp "$INPUT" "$OUTPUT"
    echo "图片已经足够小，直接复制"
    echo "输出: $OUTPUT"
    exit 0
fi

# Step 1: Resize if dimensions too large
RESIZE_DIM=$MAX_DIM
if [ "$ORIG_W" -gt "$MAX_DIM" ] || [ "$ORIG_H" -gt "$MAX_DIM" ]; then
    echo "缩放: 长边 → ${MAX_DIM}px"
    sips --resampleHeightWidthMax "$MAX_DIM" "$INPUT" --out "$OUTPUT" >/dev/null 2>&1
else
    # Convert to JPEG for better compression
    sips -s format jpeg "$INPUT" --out "$OUTPUT" >/dev/null 2>&1
fi

# Step 2: Iteratively reduce quality if still too large
CUR_SIZE=$(stat -f%z "$OUTPUT")
QUALITY=85

while [ "$CUR_SIZE" -gt "$MAX_SIZE" ] && [ "$QUALITY" -gt 10 ]; do
    echo "压缩: quality=${QUALITY}, 当前=$(echo "scale=1; $CUR_SIZE / 1048576" | bc)MB"
    sips -s formatOptions "$QUALITY" "$OUTPUT" --out "$OUTPUT" >/dev/null 2>&1
    CUR_SIZE=$(stat -f%z "$OUTPUT")
    QUALITY=$((QUALITY - 10))
done

# Step 3: If still too large, resize further
if [ "$CUR_SIZE" -gt "$MAX_SIZE" ]; then
    RESIZE_DIM=2048
    echo "进一步缩放: 长边 → ${RESIZE_DIM}px"
    sips --resampleHeightWidthMax "$RESIZE_DIM" "$OUTPUT" --out "$OUTPUT" >/dev/null 2>&1
    QUALITY=75
    CUR_SIZE=$(stat -f%z "$OUTPUT")
    while [ "$CUR_SIZE" -gt "$MAX_SIZE" ] && [ "$QUALITY" -gt 10 ]; do
        sips -s formatOptions "$QUALITY" "$OUTPUT" --out "$OUTPUT" >/dev/null 2>&1
        CUR_SIZE=$(stat -f%z "$OUTPUT")
        QUALITY=$((QUALITY - 10))
    done
fi

# Final info
FINAL_SIZE=$(stat -f%z "$OUTPUT")
FINAL_W=$(sips -g pixelWidth "$OUTPUT" | tail -1 | awk '{print $2}')
FINAL_H=$(sips -g pixelHeight "$OUTPUT" | tail -1 | awk '{print $2}')
FINAL_MB=$(echo "scale=1; $FINAL_SIZE / 1048576" | bc)
RATIO=$(echo "scale=0; $FINAL_SIZE * 100 / $ORIG_SIZE" | bc)

echo "输出: ${FINAL_W}x${FINAL_H}, ${FINAL_MB}MB (压缩率${RATIO}%)"
echo "文件: $OUTPUT"
