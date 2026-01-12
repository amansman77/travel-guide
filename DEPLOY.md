# Google Cloud Run 배포 가이드 (Docker Hub 사용)

이 문서는 Travel Guide MVP를 Google Cloud Run에 배포하는 방법을 설명합니다.  
**Docker Hub를 사용하여 과금을 피합니다** (Artifact Registry는 과금 대상).

## 사전 요구사항

1. Google Cloud Platform 계정 및 프로젝트
2. `gcloud` CLI 설치 및 인증
3. Docker 설치 및 Docker Hub 계정
4. Docker Hub 인증

## 배포 단계

### 1. Docker Hub 계정 준비

```bash
# Docker Hub에 로그인
docker login

# 사용자명과 비밀번호 입력
# 또는 Personal Access Token 사용 (권장)
```

**Personal Access Token 사용 (권장):**
1. Docker Hub 웹사이트 접속 → Account Settings → Security
2. "New Access Token" 클릭하여 토큰 생성
3. `docker login -u YOUR_USERNAME` 실행 후 토큰을 비밀번호로 입력

### 2. Google Cloud 프로젝트 설정

```bash
# 프로젝트 ID 설정
export PROJECT_ID="incubator-483707"
gcloud config set project $PROJECT_ID

# Cloud Run API 활성화
gcloud services enable run.googleapis.com
```

### 3. Docker 이미지 빌드 및 푸시

```bash
# Docker Hub 사용자명 설정
export DOCKERHUB_USERNAME="your-dockerhub-username"

# 이미지 빌드
docker build -t $DOCKERHUB_USERNAME/travel-guide-mvp:latest .

# Docker Hub에 푸시
docker push $DOCKERHUB_USERNAME/travel-guide-mvp:latest
```

### 4. Cloud Run에 배포

#### 방법 A: 환경변수로 직접 설정

```bash
# Cloud Run 서비스 배포
gcloud run deploy travel-guide-mvp \
    --image $DOCKERHUB_USERNAME/travel-guide-mvp:latest \
    --platform managed \
    --region asia-northeast3 \
    --allow-unauthenticated \
    --port 8080 \
    --memory 512Mi \
    --cpu 1 \
    --timeout 300 \
    --max-instances 10 \
    --min-instances 0 \
    --set-env-vars OPENAI_API_KEY="YOUR_OPENAI_API_KEY"
```

**중요**: `YOUR_OPENAI_API_KEY`는 실제 API 키로 변경하세요.

#### 방법 B: Secret Manager 사용 (권장 - 보안 강화)

API 키를 Secret Manager에 저장하고 사용하는 것이 더 안전합니다:

```bash
# Secret 생성
echo -n "YOUR_OPENAI_API_KEY" | gcloud secrets create openai-api-key \
    --data-file=- \
    --replication-policy="automatic"

# Cloud Run에 Secret 연결
gcloud run deploy travel-guide-mvp \
    --image $DOCKERHUB_USERNAME/travel-guide-mvp:latest \
    --platform managed \
    --region asia-northeast3 \
    --allow-unauthenticated \
    --port 8080 \
    --memory 512Mi \
    --cpu 1 \
    --timeout 300 \
    --max-instances 10 \
    --min-instances 0 \
    --set-secrets OPENAI_API_KEY=openai-api-key:latest
```

### 5. 배포 스크립트 사용 (가장 간단)

```bash
# 배포 스크립트 실행
./deploy.sh incubator-483707 asia-northeast3 YOUR_DOCKERHUB_USERNAME

# 또는 API 키를 직접 전달
./deploy.sh incubator-483707 asia-northeast3 YOUR_DOCKERHUB_USERNAME "YOUR_OPENAI_API_KEY"
```

### 6. 배포 확인

배포가 완료되면 서비스 URL이 출력됩니다:

```
Service [travel-guide-mvp] revision [travel-guide-mvp-xxxxx] has been deployed and is serving 100 percent of traffic.
Service URL: https://travel-guide-mvp-xxxxx-xx.a.run.app
```

브라우저에서 해당 URL로 접속하여 앱이 정상 작동하는지 확인하세요.

## 로컬 테스트

배포 전에 로컬에서 Docker 이미지를 테스트할 수 있습니다:

```bash
# 이미지 빌드
docker build -t travel-guide-mvp .

# 컨테이너 실행
docker run -p 8080:8080 \
    -e OPENAI_API_KEY="YOUR_OPENAI_API_KEY" \
    travel-guide-mvp
```

브라우저에서 `http://localhost:8080`으로 접속하여 테스트하세요.

## 업데이트 배포

코드 변경 후 재배포:

```bash
# 이미지 재빌드 및 푸시
docker build -t $DOCKERHUB_USERNAME/travel-guide-mvp:latest .
docker push $DOCKERHUB_USERNAME/travel-guide-mvp:latest

# Cloud Run 서비스 업데이트
gcloud run deploy travel-guide-mvp \
    --image $DOCKERHUB_USERNAME/travel-guide-mvp:latest \
    --platform managed \
    --region asia-northeast3
```

또는 배포 스크립트를 다시 실행:

```bash
./deploy.sh incubator-483707 asia-northeast3 YOUR_DOCKERHUB_USERNAME
```

## 비용 최적화

- **최소 인스턴스**: 0으로 설정하여 트래픽이 없을 때 비용 절감
- **최대 인스턴스**: 예상 트래픽에 맞게 조정
- **메모리/CPU**: 실제 사용량에 맞게 조정 (기본값: 512Mi, 1 CPU)

```bash
gcloud run services update travel-guide-mvp \
    --min-instances 0 \
    --max-instances 5 \
    --memory 256Mi \
    --cpu 0.5 \
    --region asia-northeast3
```

## Docker Hub vs Artifact Registry

### Docker Hub 장점
- ✅ **무료** (개인 사용자)
- ✅ 추가 설정 불필요
- ✅ 널리 사용되는 표준 레지스트리

### Artifact Registry 장점
- ✅ GCP와 통합
- ✅ 더 빠른 이미지 풀 속도 (같은 리전)
- ❌ **과금 발생** (스토리지 및 네트워크 사용량)

**이 프로젝트는 Docker Hub를 사용하여 비용을 절감합니다.**

## 트러블슈팅

### Docker Hub 인증 오류
```bash
# Docker Hub 재로그인
docker logout
docker login
```

### 포트 오류
- Cloud Run은 `PORT` 환경변수를 제공하지만, Streamlit은 고정 포트를 사용하므로 Dockerfile에서 8080으로 설정했습니다.

### 메모리 부족
- 메모리 사용량이 많다면 `--memory` 옵션을 증가시키세요 (예: `1Gi`, `2Gi`)

### 타임아웃
- LLM 호출이 오래 걸릴 수 있으므로 `--timeout`을 적절히 설정하세요 (최대 3600초)

### 이미지 Pull 오류
- Cloud Run이 Docker Hub에서 이미지를 pull할 때 인증이 필요할 수 있습니다.
- Public 이미지로 설정하거나, Cloud Run에서 Docker Hub 인증을 설정해야 합니다.
- Public 이미지로 설정하는 것이 가장 간단합니다 (Docker Hub에서 Repository Settings → Make Public)

## 참고 자료

- [Cloud Run 문서](https://cloud.google.com/run/docs)
- [Docker Hub 문서](https://docs.docker.com/docker-hub/)
- [Streamlit Cloud Run 배포](https://docs.streamlit.io/deploy/deploy-to-cloud-run)
