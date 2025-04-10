FROM python:3.11.11-slim-bullseye
COPY . .

RUN apt-get update && \
    apt-get install -y build-essential \
    xvfb \
    libgtk-3-0 \
    libnotify-dev \
    libgconf-2-4 \
    libnss3 \
    libxss1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install -r requirements.txt && \
    playwright install-deps  && \
    playwright install

WORKDIR /llm_browser
CMD ["xvfb-run", "python", "main.py"]

# CMD bash -c "cd llm_browser && python main.py"
# DOCKER_BUILDKIT=1 docker build --progress=plain -t llm_browser .
# docker run llm_browser
# docker inspect mongodb | grep NetworkMode
# docker run --network=hetzner_default llm_browser