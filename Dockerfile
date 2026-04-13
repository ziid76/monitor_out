FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
# 타임존 설정
ENV TZ=Asia/Seoul


WORKDIR /app
COPY requirements.txt ./
#RUN pip install --upgrade pip
RUN pip install --upgrade pip --trusted-host pypi.org --trusted-host files.pythonhosted.org
#RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
RUN apt-get update && apt-get install -y vim tzdata cron curl \
    libglib2.0-0 libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libatspi2.0-0 libx11-6 libxcomposite1 libxdamage1 libxext6 libxfixes3 \
    libxrandr2 libgbm1 libxcb1 libxkbcommon0 libpango-1.0-0 libcairo2 libasound2

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone && dpkg-reconfigure -f noninteractive tzdata
RUN rm -rf /var/lib/apt/lists/*
COPY . .

# crontab 파일 복사
COPY crontab /etc/cron.d/itms-cron
RUN chmod 0644 /etc/cron.d/itms-cron
RUN crontab /etc/cron.d/itms-cron

# 로그 디렉토리 생성
RUN mkdir -p /var/log/cron

# 시작 스크립트 생성
#COPY start.sh /start.sh
#RUN chmod +x /start.sh

#CMD ["/start.sh"]
