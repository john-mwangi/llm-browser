FROM mcr.microsoft.com/playwright/python:v1.50.0-noble
COPY . /app
RUN pip install -r /app/requirements.txt

RUN apt-get update && apt-get install -y lshw
RUN curl -fsSL https://ollama.com/install.sh | sh

# ref: https://superuser.com/questions/1325500/running-a-command-in-the-background
RUN ollama serve > /dev/null & \
    sleep 2 \
    && ollama pull llama3.2

WORKDIR /app/llm_browser

# CMD ["XX", "XX", ...] does not work
CMD bash -c "ollama serve > /dev/null & \
    ollama run llama3.2 > /dev/null & \
    xvfb-run --auto-servernum --server-num=1 --server-args='-screen 0, 1920x1080x24' python main.py"

# docker inspect mongodb | grep NetworkMode
# DOCKER_BUILDKIT=1 docker build --progress=plain -t llm_browser .
# docker run --network=hetzner_default llm_browser
# docker run --network=hetzner_default -ti llm_browser bash