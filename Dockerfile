FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ git curl libpq-dev && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "freqtrade[all]" psycopg2-binary

WORKDIR /bot

COPY strategies/ /bot/user_data/strategies/
COPY exchange/ /bot/user_data/exchange/
COPY dashboard/ /bot/dashboard/
COPY config.json /bot/config.json
COPY start.sh /bot/start.sh
COPY inject_dashboard.py /bot/inject_dashboard.py

RUN chmod +x /bot/start.sh && \
    mkdir -p /bot/user_data/data /bot/user_data/logs

RUN python3 /bot/inject_dashboard.py

EXPOSE 7860
ENV PYTHONUNBUFFERED=1

CMD ["bash", "/bot/start.sh"]
