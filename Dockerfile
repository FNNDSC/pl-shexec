# Python version can be changed, e.g.
# FROM python:3.8
# FROM docker.io/fnndsc/conda:python3.10.2-cuda11.6.0
FROM docker.io/python:3.11.0-slim-bullseye

LABEL org.opencontainers.image.authors="FNNDSC <dev@babyMRI.org>" \
      org.opencontainers.image.title="Execute shell-type commands across input spaces" \
      org.opencontainers.image.description="A ChRIS plugin that uses pfdo_run to execute shell-type commands across input spaces "

WORKDIR /usr/local/src/pl-shexec

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
ARG extras_require=none
# RUN pip install ".[${extras_require}]"

RUN   pip install --upgrade pip                                   && \
      pip install ".[${extras_require}]"                          && \
      pip install -r requirements.txt                             && \
      pip install .                                               && \
      apt update  && apt -y upgrade                               && \
      apt install -y zip unzip inetutils-tools                    && \
      apt install -y bc binutils  perl psmisc                     && \
      apt install -y tar uuid-dev                                 && \
      apt install -y neovim                                       && \
      apt install -y imagemagick                                  && \
      apt install -y tzdata                                       && \
      apt-get install -y locales                                  && \
      export LANGUAGE=en_US.UTF-8                                 && \
      export LANG=en_US.UTF-8                                     && \
      export LC_ALL=en_US.UTF-8                                   && \
      locale-gen en_US.UTF-8                                      && \
      dpkg-reconfigure locales

CMD ["shexec", "--man"]
