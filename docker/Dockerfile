FROM continuumio/miniconda3 AS build

RUN git clone http://gitlab.forge-idi.ign.fr/Lidar/lidarExpress.git

WORKDIR /lidarExpress

RUN conda env create -n lidarexpress -f environment.yml

ENTRYPOINT ["conda", "run", "-n", "lidarexpress"]
