COVERAGE_ANNOTATION=coverage_annotations
TEST_CMD=manage.py test orchestra beanstalk_dispatch

clean:
	find . -name '*.pyo' -delete
	find . -name '*.pyc' -delete
	find . -name __pycache__ -delete
	find . -name '*~' -delete

lint:
	flake8 . && gulp lint

test: lint
	cd example_project && python3 $(TEST_CMD)

coverage:
	cd example_project && \
	  coverage run --source=../orchestra $(TEST_CMD)

coveralls:
	cd example_project && coveralls

npm_install:
	npm install -g gulp
	npm install

build_dist: npm_install
	gulp build

build_docs:
	cd docs && make html
