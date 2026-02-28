PYTHON ?= python3

.PHONY: install run test lint build

install:
	$(PYTHON) -m pip install --upgrade pip

run:
	PYTHONPATH=src $(PYTHON) src/main.py

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

lint:
	$(PYTHON) -m py_compile src/*.py src/app/*.py tests/*.py

build:
	docker build -t pulseboard:local .
