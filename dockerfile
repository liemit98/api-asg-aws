FROM alpine:latest
LABEL maintainer="docker@ix.ai" \
      ai.ix.repository="ix.ai/alertmanager-telegram-bot"

COPY api.py api.py

RUN apk --no-cache upgrade && \
    apk --no-cache add python3 py3-pip py3-waitress py3-flask py3-boto3

EXPOSE 5000

ENTRYPOINT ["python3", "api.py"]