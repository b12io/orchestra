COVERAGE_ANNOTATION=coverage_annotations
TEST_CMD=manage.py test orchestra beanstalk_dispatch --with-xunit --exclude=assert_test*
GULP := $(shell command -v gulp 2> /dev/null)

clean:
	find . -name '*.pyo' -delete
	find . -name '*.pyc' -delete
	find . -name __pycache__ -delete
	find . -name '*~' -delete

lint:
	flake8 . && isort --check-only --recursive .
	gulp lint --production
	!(find . -wholename '**migrations**/*.py' -print0 | xargs -0 grep 'RemoveField\|DeleteModel\|AlterModelTable\|AlterUniqueTogether\|RunSQL\|RunPython\|SeparateDatabaseAndState' | grep -v '# manually-reviewed') || { echo "Migrations need to be manually reviewed!"; exit 1; }
	!(cd example_project && python3 manage.py makemigrations --dry-run --exit) || { printf "Migrations need to be created. Try: \n\t python3 manage.py makemigrations\n"; exit 1; }

test: lint
	cd example_project && python3 $(TEST_CMD)

coverage:
	cd example_project && \
	  coverage run --rcfile=../.coveragerc $(TEST_CMD)

coveralls:
	cd example_project && coveralls

npm_install:
ifndef GULP
	npm install -g gulp
endif
	npm install

gulp_build: npm_install
	gulp build --production

build_docs:
	cd docs && make html
