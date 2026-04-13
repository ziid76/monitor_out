# Web Monitor (Lightweight Edition)

웹사이트의 가동 상태를 실시간으로 모니터링하고 가시화하는 경량화된 웹 애플리케이션입니다.

## 시스템 구성 및 아키텍처

본 프로젝트는 최소한의 자원으로 운영되도록 SQLite와 Celery를 기반으로 구성되어 있습니다.

### 주요 컴포넌트 역할

#### 1. Redis (Message Broker)
- **역할**: Celery Beat와 Worker 사이의 통신을 담당하는 메시지 브로커입니다.
- **설명**: 스케줄러(Beat)가 발행한 작업(Task) 메시지를 큐에 담아두고, 실행기(Worker)가 이를 가져가 처리할 수 있도록 중간 매개체 역할을 합니다.

#### 2. Celery Beat (Scheduler)
- **역할**: 주기적인 작업을 관리하고 발행하는 스케줄러입니다.
- **설명**: `db.sqlite3` 설정에 등록된 각 사이트별 모니터링 주기를 확인하여, 정해진 시간마다 "점검 작업"을 Redis 큐에 집어넣습니다.

#### 3. Celery Worker (Executor)
- **역할**: 실제 모니터링 작업을 수행하는 실행기입니다.
- **설명**: Redis 큐에 쌓여 있는 작업 메시지를 실시간으로 감시하며, 메시지가 들어오면 즉시 해당 사이트의 HTTP 요청을 보내 상태를 확인하고 그 결과를 DB에 저장합니다.

## 시작하기

### 실행 환경 설정
`.env` 파일을 생성하거나 수정하여 필요한 설정을 입력합니다.

### Docker Compose로 실행
```bash
docker-compose up -d --build
```

### 초기 설정 (관리자 계정 및 작업 등록)
애플리케이션 실행 후 컨브레인 내에서 다음 명령어를 실행하거나, 웹 대시보드의 '옵션 설정' 메뉴를 이용하세요.
```bash
docker-compose exec web python manage.py setup_tasks
```

## 기술 스택
- **Backend**: Django (Python)
- **Database**: SQLite
- **Task Queue**: Celery, Redis
- **Frontend**: Tailwind CSS, Vanilla JS
