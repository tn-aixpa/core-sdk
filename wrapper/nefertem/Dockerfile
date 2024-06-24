FROM python:3.9

# Repo info
LABEL org.opencontainers.image.source=https://github.com/scc-digitalhub/digitalhub-core
ARG DHUB_VERSION=

# Set working dir
WORKDIR /app/

# Install runtime and requirements
RUN pip install digitalhub_runtime_nefertem[local]==0.5.0

# Get nefertem
ARG NEFERTEM_VERSION=2.0.6
RUN wget https://github.com/scc-digitalhub/nefertem/archive/refs/tags/$NEFERTEM_VERSION.zip
RUN unzip $NEFERTEM_VERSION.zip
RUN mv nefertem-$NEFERTEM_VERSION nefertem
RUN rm $NEFERTEM_VERSION.zip

# Install nefertem plugins
RUN pip install nefertem/plugins/frictionless*
RUN pip install nefertem/plugins/duckdb*
RUN pip install nefertem/plugins/sqlalchemy*
RUN pip install nefertem/plugins/ydata*

# Copy wrapper and set entry point
COPY wrapper.py /app/

# Cleanup folders
RUN rm -rf digitalhub-sdk nefertem

ENTRYPOINT ["python", "wrapper.py"]
