#!/bin/bash

# Google Cloud Run 배포 스크립트 (Docker Hub 사용)
# 사용법: ./deploy.sh [PROJECT_ID] [REGION] [DOCKERHUB_USERNAME] [OPENAI_API_KEY] [LANGSMITH_API_KEY]
# 또는 secrets.toml에서 자동으로 읽어옵니다.

set -e

# secrets.toml에서 설정 읽기 (있는 경우)
SECRETS_FILE=".streamlit/secrets.toml"
if [ -f "$SECRETS_FILE" ]; then
    echo "📋 secrets.toml에서 설정 읽는 중..."
    # TOML 파싱 (간단한 방식)
    if [ -z "$PROJECT_ID" ]; then
        PROJECT_ID=$(grep "^PROJECT_ID" "$SECRETS_FILE" | awk -F'"' '{print $2}' || echo "")
    fi
    if [ -z "$REGION" ]; then
        REGION=$(grep "^REGION" "$SECRETS_FILE" | awk -F'"' '{print $2}' || echo "")
    fi
    if [ -z "$DOCKERHUB_USERNAME" ]; then
        DOCKERHUB_USERNAME=$(grep "^DOCKERHUB_USERNAME" "$SECRETS_FILE" | awk -F'"' '{print $2}' || echo "")
    fi
    if [ -z "$DOCKERHUB_TOKEN" ]; then
        DOCKERHUB_TOKEN=$(grep "^DOCKERHUB_PERSONAL_ACCESS_TOKEN" "$SECRETS_FILE" | awk -F'"' '{print $2}' || echo "")
    fi
    if [ -z "$OPENAI_API_KEY" ]; then
        OPENAI_API_KEY=$(grep "^OPENAI_API_KEY" "$SECRETS_FILE" | grep -v "^#" | awk -F'"' '{print $2}' | head -1 || echo "")
    fi
    if [ -z "$LANGSMITH_API_KEY" ]; then
        LANGSMITH_API_KEY=$(grep "^LANGSMITH_API_KEY" "$SECRETS_FILE" | awk -F'"' '{print $2}' || echo "")
    fi
fi

# 명령줄 인자로 덮어쓰기 (우선순위: 명령줄 > secrets.toml > 기본값)
PROJECT_ID=${1:-${PROJECT_ID:-"YOUR_PROJECT_ID"}}
REGION=${2:-${REGION:-"asia-northeast3"}}
DOCKERHUB_USERNAME=${3:-${DOCKERHUB_USERNAME:-""}}
OPENAI_API_KEY=${4:-${OPENAI_API_KEY:-""}}
LANGSMITH_API_KEY=${5:-${LANGSMITH_API_KEY:-""}}

# 색상 출력
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Travel Guide MVP 배포 시작 (Docker Hub 사용)${NC}"

# 설정 확인 및 출력
echo -e "${YELLOW}📋 배포 설정 확인:${NC}"
if [ -f "$SECRETS_FILE" ]; then
    echo -e "   - secrets.toml: ✅ 발견됨"
else
    echo -e "   - secrets.toml: ⚠️  없음 (명령줄 인자 사용)"
fi
echo -e "   - PROJECT_ID: ${PROJECT_ID:-❌ 없음}"
echo -e "   - REGION: ${REGION:-❌ 없음}"
echo -e "   - DOCKERHUB_USERNAME: ${DOCKERHUB_USERNAME:-❌ 없음}"
echo -e "   - OPENAI_API_KEY: ${OPENAI_API_KEY:+✅ 설정됨}${OPENAI_API_KEY:-❌ 없음}"
echo -e "   - LANGSMITH_API_KEY: ${LANGSMITH_API_KEY:+✅ 설정됨}${LANGSMITH_API_KEY:-❌ 없음}"

# 프로젝트 ID 확인
if [ "$PROJECT_ID" == "YOUR_PROJECT_ID" ] || [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}❌ 프로젝트 ID를 설정해주세요.${NC}"
    echo "사용법: ./deploy.sh PROJECT_ID [REGION] [DOCKERHUB_USERNAME] [OPENAI_API_KEY]"
    echo "또는 secrets.toml에 PROJECT_ID 추가"
    exit 1
fi

# Docker Hub 사용자명 확인
if [ -z "$DOCKERHUB_USERNAME" ]; then
    echo -e "${RED}❌ Docker Hub 사용자명을 설정해주세요.${NC}"
    echo "사용법: ./deploy.sh PROJECT_ID REGION DOCKERHUB_USERNAME [OPENAI_API_KEY]"
    echo "또는 secrets.toml에 DOCKERHUB_USERNAME 추가"
    exit 1
fi

# gcloud 프로젝트 설정
echo -e "${YELLOW}📋 프로젝트 설정: $PROJECT_ID${NC}"
gcloud config set project $PROJECT_ID

# 필요한 API 활성화
echo -e "${YELLOW}🔧 Cloud Run API 활성화 중...${NC}"
gcloud services enable run.googleapis.com --quiet

# Docker Hub 인증 확인 (Cloud Build 사용 시 로컬 Docker 불필요)
echo -e "${YELLOW}🔐 Docker Hub 인증 확인 중...${NC}"
# Cloud Build를 사용하므로 로컬 Docker daemon은 필요 없음
# Docker Hub Personal Access Token은 환경변수 DOCKERHUB_TOKEN으로 전달됨

# Docker 이미지 빌드 및 푸시
IMAGE_NAME="travel-guide-mvp"
# 타임스탬프를 포함한 태그로 강제 새 이미지 사용
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
IMAGE_TAG="$DOCKERHUB_USERNAME/$IMAGE_NAME:$TIMESTAMP"
IMAGE_TAG_LATEST="$DOCKERHUB_USERNAME/$IMAGE_NAME:latest"

echo -e "${YELLOW}🔨 Cloud Build로 이미지 빌드 및 Docker Hub 푸시 중 (amd64 플랫폼)...${NC}"

# Docker Hub Personal Access Token 확인
# 우선순위: 환경변수 > secrets.toml > 사용자 입력
if [ -z "$DOCKERHUB_TOKEN" ]; then
    # 환경변수 확인
    if [ -n "${DOCKERHUB_TOKEN_ENV:-}" ]; then
        DOCKERHUB_TOKEN="$DOCKERHUB_TOKEN_ENV"
        echo -e "${GREEN}✅ 환경변수에서 Docker Hub Token 사용${NC}"
    else
        echo -e "${YELLOW}📝 Docker Hub Personal Access Token이 필요합니다.${NC}"
        echo -e "${YELLOW}   Docker Hub → Account Settings → Security → New Access Token${NC}"
        echo -e "${YELLOW}   또는 환경변수로 설정: export DOCKERHUB_TOKEN='YOUR_TOKEN'${NC}"
        echo -e "${YELLOW}   또는 secrets.toml에 DOCKERHUB_PERSONAL_ACCESS_TOKEN 추가${NC}"
        read -sp "Docker Hub Personal Access Token을 입력하세요: " DOCKERHUB_TOKEN
        echo ""
        
        if [ -z "$DOCKERHUB_TOKEN" ]; then
            echo -e "${RED}❌ Docker Hub Token이 필요합니다.${NC}"
            echo -e "${YELLOW}   환경변수로 설정: export DOCKERHUB_TOKEN='YOUR_TOKEN'${NC}"
            echo -e "${YELLOW}   또는 secrets.toml에 DOCKERHUB_PERSONAL_ACCESS_TOKEN 추가${NC}"
            exit 1
        fi
    fi
else
    echo -e "${GREEN}✅ secrets.toml에서 Docker Hub Token 사용${NC}"
fi

# Cloud Build 설정 파일 생성
CLOUDBUILD_FILE="/tmp/cloudbuild-$$.yaml"

# Cloud Build에서 substitution 변수로 토큰 전달
cat > $CLOUDBUILD_FILE <<EOF
steps:
# Docker Hub에 로그인
- name: 'gcr.io/cloud-builders/docker'
  entrypoint: 'bash'
  args:
    - '-c'
    - |
      echo "\${_DOCKERHUB_TOKEN}" | docker login -u "$DOCKERHUB_USERNAME" --password-stdin
# amd64 플랫폼으로 빌드 (타임스탬프 태그와 latest 태그 모두)
- name: 'gcr.io/cloud-builders/docker'
  args: 
    - 'build'
    - '--platform'
    - 'linux/amd64'
    - '-t'
    - '$IMAGE_TAG'
    - '-t'
    - '$IMAGE_TAG_LATEST'
    - '.'
# Docker Hub에 푸시 (두 태그 모두)
- name: 'gcr.io/cloud-builders/docker'
  args: ['push', '$IMAGE_TAG']
- name: 'gcr.io/cloud-builders/docker'
  args: ['push', '$IMAGE_TAG_LATEST']
substitutions:
  _DOCKERHUB_TOKEN: '${DOCKERHUB_TOKEN}'
EOF

echo -e "${YELLOW}📦 Cloud Build로 amd64 이미지 빌드 및 Docker Hub 푸시 중...${NC}"
echo -e "${YELLOW}   이미지 태그: $IMAGE_TAG (및 latest)${NC}"
gcloud builds submit --config=$CLOUDBUILD_FILE .

# 임시 파일 정리
rm -f $CLOUDBUILD_FILE

# Secret Manager 사용 여부 확인 및 환경변수 설정
ENV_VARS=""
SECRET_FLAGS=""

if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${YELLOW}⚠️  OPENAI_API_KEY가 제공되지 않았습니다.${NC}"
    echo -e "${YELLOW}Secret Manager를 사용하거나 환경변수로 직접 설정하세요.${NC}"
    
    # Secret Manager 확인
    if gcloud secrets describe openai-api-key &>/dev/null; then
        echo -e "${GREEN}✅ Secret Manager의 openai-api-key 사용${NC}"
        SECRET_FLAGS="--set-secrets OPENAI_API_KEY=openai-api-key:latest"
    else
        echo -e "${RED}❌ Secret Manager에 openai-api-key가 없습니다.${NC}"
        echo "Secret 생성: echo -n 'YOUR_KEY' | gcloud secrets create openai-api-key --data-file=-"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  환경변수로 직접 설정합니다 (보안상 권장하지 않음)${NC}"
    ENV_VARS="OPENAI_API_KEY=$OPENAI_API_KEY"
fi

# LangSmith 환경변수 추가 (선택적)
if [ -n "$LANGSMITH_API_KEY" ]; then
    echo -e "${GREEN}✅ LangSmith 환경변수 추가${NC}"
    if [ -n "$ENV_VARS" ]; then
        ENV_VARS="$ENV_VARS,LANGSMITH_TRACING=true,LANGSMITH_ENDPOINT=https://api.smith.langchain.com,LANGSMITH_API_KEY=$LANGSMITH_API_KEY,LANGSMITH_PROJECT=travel-guide"
    else
        ENV_VARS="LANGSMITH_TRACING=true,LANGSMITH_ENDPOINT=https://api.smith.langchain.com,LANGSMITH_API_KEY=$LANGSMITH_API_KEY,LANGSMITH_PROJECT=travel-guide"
    fi
fi

# 환경변수 플래그 설정
if [ -n "$ENV_VARS" ]; then
    if [ -n "$SECRET_FLAGS" ]; then
        SECRET_FLAG="$SECRET_FLAGS --set-env-vars $ENV_VARS"
    else
        SECRET_FLAG="--set-env-vars $ENV_VARS"
    fi
else
    SECRET_FLAG="$SECRET_FLAGS"
fi

# Cloud Run 배포
SERVICE_NAME="travel-guide-mvp"

echo -e "${YELLOW}🚀 Cloud Run에 배포 중...${NC}"
gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_TAG \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --port 8080 \
    --memory 1Gi \
    --cpu 2 \
    --timeout 300 \
    --max-instances 10 \
    --min-instances 0 \
    $SECRET_FLAG

# 서비스 URL 출력
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.url)')

echo -e "${GREEN}✅ 배포 완료!${NC}"
echo -e "${GREEN}🌐 서비스 URL: $SERVICE_URL${NC}"
echo -e "${GREEN}📦 Docker Hub 이미지: $IMAGE_TAG${NC}"
