COVERAGE_ANNOTATION=coverage_annotations
TEST_CMD=manage.py test orchestra beanstalk_dispatch

clean:
	find . -name '*.pyo' -delete
	find . -name '*.pyc' -delete
	find . -name __pycache__ -delete
	find . -name '*~' -delete

lint:
	flake8 .

test: build_docs lint
	cd example_project && python3 $(TEST_CMD)

coverage:
	cd example_project && \
	  coverage run --source=../orchestra $(TEST_CMD)

coverage_artifacts:
	cd example_project && \
	  coverage html -d coverage_artifacts

test_coverage:
	cd example_project && \
	  coverage erase && \
	  rm -rf $(COVERAGE_ANNOTATION) && \
	  coverage run --source=../orchestra $(TEST_CMD) && \
	  coverage annotate -d $(COVERAGE_ANNOTATION) && \
	  coverage report && \
	  echo 'Annotated source in `example_project/$(COVERAGE_ANNOTATION)` directory'

build_docs:
	cd docs && make html
