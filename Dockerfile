FROM python:3.13-alpine

COPY . /app

# hadolint ignore=DL3018
RUN apk add --virtual deps --no-cache gcc musl-dev && \
    pip install --no-cache-dir /app && \
    apk del deps

ENTRYPOINT ["vodafone-station-cli"]
