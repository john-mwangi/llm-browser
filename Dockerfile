# ref: https://airflow.apache.org/docs/apache-airflow/stable/start.html

FROM python:3.11.11-slim-bullseye

ENV AIRFLOW_HOME=/home/airflow
ENV AIRFLOW__CORE__LOAD_EXAMPLES=False

ARG PYTHON_VERSION=3.11
ARG AIRFLOW_VERSION=2.10.5
ARG CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"

WORKDIR ${AIRFLOW_HOME}
COPY requirements.txt .

# RUN pip install "apache-airflow==${AIRFLOW_VERSION}" --constraint "${CONSTRAINT_URL}"
RUN pip install -r requirements.txt
RUN pip install "apache-airflow==${AIRFLOW_VERSION}"

# default username and password will be in the startup logs
# /home/airflow/standalone_admin_password.txt
CMD ["airflow", "standalone"]