FROM lidar_hd/lidar_express AS build

WORKDIR /lidarExpress

# https://pythonspeed.com/articles/conda-docker-image-size/
# Install conda-pack:
RUN conda install -c conda-forge conda-pack

# Use conda-pack to create a standalone enviornment
# in /venv:
RUN conda-pack -n lidarexpress -o /tmp/env.tar && \
  mkdir /venv && cd /venv && tar xf /tmp/env.tar && \
  rm /tmp/env.tar

# We've put venv in same path it'll be in final image,
# so now fix up paths:
RUN /venv/bin/conda-unpack


# The runtime-stage image; we can use Debian as the
# base image since the Conda env also includes Python
# for us.
FROM debian:buster AS runtime

# Copy /venv from the previous stage:
COPY --from=build /venv /venv
COPY --from=build /lidarExpress /lidarExpress

# When image is run, run the code with the environment
# activated:
SHELL ["/bin/bash", "-c"]
ENV PATH=/venv/bin:$PATH

WORKDIR /lidarExpress
