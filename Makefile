setup: requirements.txt
	pip3 install -r requirements.txt

requirements:
	pip3 freeze > requirements.txt

test:
	python3 -m unittest discover . -b

run:
	python3 src/main.py

recent:
	python3 src/cron_recent_listens.py

missing:
	python3 src/cron_load_unknown_tracks.py

clean: clean-build clean-pyc clean-test

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test:
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/
