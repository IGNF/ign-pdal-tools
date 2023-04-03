FROM continuumio/miniconda3 AS build

RUN git clone http://gitlab.forge-idi.ign.fr/Lidar/pdalTools.git

WORKDIR /pdalTools

RUN conda env create -n pdaltools -f environment.yml

ENTRYPOINT ["conda", "run", "--no-capture-output", "-n", "pdaltools"]
