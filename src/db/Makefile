.PHONY: install migrate revision sql

install:
	python -m pip install -e .

migrate:
	alembic -c alembic.ini upgrade head

revision:
	alembic -c alembic.ini revision --autogenerate -m "$(m)"

sql:
	alembic -c alembic.ini upgrade head --sql
