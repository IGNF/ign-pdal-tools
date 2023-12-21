# Makefile to manage main tasks
# cf. https://blog.ianpreston.ca/conda/python/bash/2020/05/13/conda_envs.html#makefile

# Oneshell means I can run multiple lines in a recipe in the same shell, so I don't have to
# chain commands together with semicolon
.ONESHELL:
SHELL = /bin/bash


##############################
# Install
##############################

mamba-env-create:
	mamba env create -n pdaltools -f environment.yml

mamba-env-update:
	mamba env update -n pdaltools -f environment.yml

install:
	pip install -e .


##############################
# Dev/Contrib tools
##############################

testing:
	python -m pytest ./test -s --log-cli-level DEBUG -m "not geoportail"

testing_full:
	python -m pytest ./test -s --log-cli-level DEBUG

install-precommit:
	pre-commit install


##############################
# Build/deploy pip lib
##############################

deploy: check
	twine upload dist/*

check: dist/ign-pdal-tool*.tar.gz
	twine check dist/*

dist/ign-pdal-tool*.tar.gz:
	python -m build

build: clean
	python -m build

clean:
	rm -rf tmp
	rm -rf ign_pdal_tools.egg-info
	rm -rf dist

##############################
# Build/deploy Docker image
##############################

PROJECT_NAME=ignimagelidar/ign-pdal-tools
VERSION=`python -m pdaltools._version`

docker-build: clean
	docker build --no-cache -t ${PROJECT_NAME}:${VERSION} -f Dockerfile .

docker-test:
	docker run --rm -it ${PROJECT_NAME}:${VERSION} python -m pytest -s

docker-remove:
	docker rmi -f `docker images | grep ${PROJECT_NAME} | tr -s ' ' | cut -d ' ' -f 3`

docker-deploy:
	docker push ${PROJECT_NAME}:${VERSION}
