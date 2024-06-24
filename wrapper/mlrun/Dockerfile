FROM python:3.9

# Repo info
LABEL org.opencontainers.image.source=https://github.com/scc-digitalhub/digitalhub-core
ARG DHUB_VERSION=

# Set working dir
WORKDIR /app/

# Install runtime and requirements
RUN pip install digitalhub_runtime_mlrun[local]==0.5.0

# Copy wrapper and set entry point
COPY wrapper.py /app/

ENTRYPOINT ["python", "wrapper.py"]
