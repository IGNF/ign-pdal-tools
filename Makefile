# Makefile to manage main tasks
# cf. https://blog.ianpreston.ca/conda/python/bash/2020/05/13/conda_envs.html#makefile

# Oneshell means I can run multiple lines in a recipe in the same shell, so I don't have to
# chain commands together with semicolon
.ONESHELL:
SHELL = /bin/bash
deploy: check
	twine upload dist/*

check: dist/ign-pdal-tool*.tar.gz 
	twine check dist/*

dist/ign-pdal-tool*.tar.gz:
	python -m build

build: clean
	python -m build

install:
	pip install -e .

testing:
	python -m pytest ./test -s --log-cli-level DEBUG

clean:
	rm -rf tmp
	rm -rf ign_pdal_tools.egg-info
	rm -rf dist

mamba-env-create:
	mamba env create -n pdaltools -f environment.yml

mamba-env-update:
	mamba env update -n pdaltools -f environment.yml

docker-build: clean
	docker build --no-cache -t lidar_hd/pdal_tools:`python pdaltools/_version.py` -f Dockerfile .

docker-test:
	docker run --rm -it lidar_hd/pdal_tools:`python pdaltools/_version.py` python -m pytest -s

docker-remove:
	docker rmi -f `docker images | grep pdal_tools | tr -s ' ' | cut -d ' ' -f 3`
