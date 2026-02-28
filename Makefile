.PHONY: run test init-db daily

run:
	python3 -m src.server

test:
	python3 -m unittest discover -s tests -v

init-db:
	python3 scripts/run_daily.py

daily:
	python3 scripts/run_daily.py
