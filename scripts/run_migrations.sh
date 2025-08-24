set -e


if [ -z "$(ls -A migrations/versions)" ]; then
    alembic -c alembic.ini revision --autogenerate -m "Initial commit"
fi

alembic -c alembic.ini upgrade head