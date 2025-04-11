FROM mcr.microsoft.com/playwright/python:v1.50.0-noble
COPY . /app
RUN curl -fsSL https://ollama.com/install.sh | sh && ollama pull llama3.2
RUN pip install -r /app/requirements.txt
WORKDIR /app/llm_browser

# CMD ["XX", "XX", ...] does not work
CMD bash -c "xvfb-run --auto-servernum --server-num=1 --server-args='-screen 0, 1920x1080x24' python main.py"

# docker inspect mongodb | grep NetworkMode
# DOCKER_BUILDKIT=1 docker build --progress=plain -t llm_browser .
# docker run --network=hetzner_default llm_browser
# docker run --network=hetzner_default -ti llm_browser bash