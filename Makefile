COVERAGE_ANNOTATION=coverage_annotations
TEST_CMD=manage.py test orchestra beanstalk_dispatch

clean:
	find . -name '*.pyo' -delete
	find . -name '*.pyc' -delete
	find . -name __pycache__ -delete
	find . -name '*~' -delete

lint:
	flake8 . && gulp lint --production

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

gulp_build: npm_install
	gulp build --production

build_docs:
	cd docs && make html
