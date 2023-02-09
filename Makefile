# Makefile to manage main tasks
# cf. https://blog.ianpreston.ca/conda/python/bash/2020/05/13/conda_envs.html#makefile

# Oneshell means I can run multiple lines in a recipe in the same shell, so I don't have to
# chain commands together with semicolon
.ONESHELL:

deploy: check
	twine upload dist/*

check: dist/ign-pdal-tool*.tar.gz 
	twine check dist/*

dist/ign-pdal-tool*.tar.gz:
	python -m build

build:
	python -m build

install:
	pip install -e .

testing:
	python -m pytest ./test -s --log-cli-level DEBUG