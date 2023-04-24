FROM mambaorg/micromamba:latest as build

WORKDIR /pdalTools
COPY . .

RUN micromamba env create -n pdaltools -f environment.yml

ENTRYPOINT ["conda", "run", "--no-capture-output", "-n", "pdaltools"]
