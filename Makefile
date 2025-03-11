verify: check-code test

check-code: check-format check-types

check-format:
	black --check src tests

check-types:
	mypy src

format:
	black src tests

test:
	pytest tests
