set -e


if [ -z "$(ls -A migrations/versions)" ]; then
    alembic -c migrations/alembic.ini revision --autogenerate -m "Initial commit"
fi

alembic -c migrations/alembic.ini upgrade head