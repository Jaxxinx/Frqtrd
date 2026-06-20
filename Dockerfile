FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ git curl libpq-dev && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir freqtrade[all] psycopg2-binary

WORKDIR /bot

COPY strategies/ /bot/user_data/strategies/
COPY exchange/ /bot/user_data/exchange/
COPY dashboard/ /bot/dashboard/
COPY config.json /bot/config.json
COPY start.sh /bot/start.sh

RUN chmod +x /bot/start.sh && \
    mkdir -p /bot/user_data/data /bot/user_data/logs

# Inject custom dashboard route into freqtrade
RUN python3 -c " \
import freqtrade.rpc.api_server.web_ui as w; \
src = open(w.__file__).read(); \
if '/custom' not in src: \
    import shutil; \
    shutil.copy('/bot/dashboard/custom_dashboard.html', w.__file__.replace('web_ui.py','ui/custom_dashboard.html')); \
    inject = '''\n\n@router_ui.get(\"/custom\")\nasync def custom_dashboard():\n    return FileResponse(str(Path(__file__).parent / \"ui/custom_dashboard.html\"))\n'''; \
    open(w.__file__,'w').write(src.replace('@router_ui.get(\"/{rest_of_path:path}\")', inject + '\n\n@router_ui.get(\"/{rest_of_path:path}\")')); \
    print('Custom dashboard injected'); \
else: \
    print('Custom dashboard already present') \
"

EXPOSE 7860
ENV PYTHONUNBUFFERED=1

CMD ["bash", "/bot/start.sh"]
