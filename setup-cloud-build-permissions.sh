#!/bin/bash

# Cloud Build 권한 설정 스크립트
# 사용법: ./setup-cloud-build-permissions.sh [PROJECT_ID] [YOUR_EMAIL]

PROJECT_ID=${1:-""}
YOUR_EMAIL=${2:-""}

echo "🔐 Cloud Build 권한 설정"
echo "프로젝트: $PROJECT_ID"
echo "사용자: $YOUR_EMAIL"
echo ""

# Cloud Build Service Account 확인
CLOUDBUILD_SA="${PROJECT_ID}@cloudbuild.gserviceaccount.com"

echo "1. Cloud Build Service Account에 권한 부여 중..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${CLOUDBUILD_SA}" \
    --role="roles/run.admin" \
    --condition=None

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${CLOUDBUILD_SA}" \
    --role="roles/iam.serviceAccountUser" \
    --condition=None

echo ""
echo "2. 사용자에게 Cloud Build 권한 부여 중..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="user:${YOUR_EMAIL}" \
    --role="roles/cloudbuild.builds.editor" \
    --condition=None

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="user:${YOUR_EMAIL}" \
    --role="roles/storage.admin" \
    --condition=None

echo ""
echo "✅ 권한 설정 완료!"
echo ""
echo "다시 배포를 시도하세요:"
echo "./deploy.sh $PROJECT_ID asia-northeast3 YOUR_DOCKERHUB_USERNAME"
