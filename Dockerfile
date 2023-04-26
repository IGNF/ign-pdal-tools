FROM mambaorg/micromamba:latest as build

WORKDIR /pdalTools
COPY . .

RUN micromamba env create -n pdaltools -f environment.yml

ENV ENV_NAME pdaltools
ARG MAMBA_DOCKERFILE_ACTIVATE=1
USER root
