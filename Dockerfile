FROM docker.io/python:3.12-slim

LABEL org.opencontainers.image.authors="FNNDSC <dev@babyMRI.org>" \
      org.opencontainers.image.title="Execute shell-type commands across input spaces" \
      org.opencontainers.image.description="A ChRIS DS plugin that runs a shell-type command over every file of its input tree, on pfdo_run"

ENV LANG=en_US.UTF-8 LANGUAGE=en_US.UTF-8 LC_ALL=en_US.UTF-8

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bc coreutils dcmtk imagemagick locales perl psmisc tar tzdata unzip zip \
    && sed -i 's/^# *en_US.UTF-8/en_US.UTF-8/' /etc/locale.gen \
    && locale-gen \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/local/src/pl-shexec
COPY . .
RUN pip install --no-cache-dir .

CMD ["shexec", "--man", "/tmp", "/tmp"]
