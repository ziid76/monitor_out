FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Seoul

WORKDIR /app

# 시스템 의존성 설치 (최소화: cron, tzdata, lxml용 라이브러리)
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    tzdata \
    libxml2 \
    curl \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# 파이썬 라이브러리 설치
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

# Crontab 설정
COPY crontab /etc/cron.d/monitor-cron
RUN chmod 0644 /etc/cron.d/monitor-cron \
    && crontab /etc/cron.d/monitor-cron \
    && mkdir -p /var/log/cron

# 시작 스크립트 실행 권한 부여 및 실행
RUN chmod +x start.sh
CMD ["./start.sh"]
