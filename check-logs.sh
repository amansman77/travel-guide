#!/bin/bash

# Cloud Run 서비스 로그 확인 스크립트
# 사용법: ./check-logs.sh [PROJECT_ID] [REGION] [SERVICE_NAME]

PROJECT_ID=${1:-"incubator-483707"}
REGION=${2:-"asia-northeast3"}
SERVICE_NAME=${3:-"travel-guide-mvp"}

echo "📋 Cloud Run 서비스 로그 확인"
echo "프로젝트: $PROJECT_ID"
echo "리전: $REGION"
echo "서비스: $SERVICE_NAME"
echo ""

# 최신 리비전 가져오기
LATEST_REVISION=$(gcloud run revisions list \
    --service=$SERVICE_NAME \
    --region=$REGION \
    --project=$PROJECT_ID \
    --format="value(name)" \
    --limit=1 \
    --sort-by=~metadata.creationTimestamp)

if [ -z "$LATEST_REVISION" ]; then
    echo "❌ 리비전을 찾을 수 없습니다."
    exit 1
fi

echo "최신 리비전: $LATEST_REVISION"
echo ""
echo "=== 최근 로그 (최근 50줄) ==="
echo ""

gcloud logging read \
    "resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME AND resource.labels.revision_name=$LATEST_REVISION" \
    --project=$PROJECT_ID \
    --limit=50 \
    --format="table(timestamp,severity,textPayload,jsonPayload.message)" \
    --freshness=1h
