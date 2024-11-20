FROM python:3.9

# Repo info
LABEL org.opencontainers.image.source=https://github.com/scc-digitalhub/digitalhub-sdk
ARG VERSION_LOWER=0.9.0b0
ARG VERSION_UPPER=0.10.0

# Set working dir
WORKDIR /app/

# Install digitalhub-core
RUN python -m pip install "digitalhub[pandas]>=${VERSION_LOWER}, <${VERSION_UPPER}" \
                          "digitalhub-runtime-kfp[local]>=${VERSION_LOWER}, <${VERSION_UPPER}" && \
    python -m pip install "digitalhub-runtime-python>=${VERSION_LOWER}, <${VERSION_UPPER}" \
                          "digitalhub-runtime-container>=${VERSION_LOWER}, <${VERSION_UPPER}" \
                          "digitalhub-runtime-modelserve>=${VERSION_LOWER}, <${VERSION_UPPER}" \
                          "digitalhub-runtime-dbt>=${VERSION_LOWER}, <${VERSION_UPPER}" --no-deps

# Copy wrapper and set entry point
COPY wrapper.py /app/
COPY step.py /app/

# Add nonroot group and user
RUN useradd -r -m -u 8877 nonroot && \
    chown -R nonroot /app
USER 8877

ENTRYPOINT ["python", "wrapper.py"]
