import os
import importlib
from sqlalchemy import inspect


def test_create_tables(tmp_path):
    os.environ['DATABASE_URL'] = f"sqlite:///{tmp_path}/test.db"
    from shared import config
    importlib.reload(config)
    from shared import database
    importlib.reload(database)

    database.create_tables()
    insp = inspect(database.engine)
    assert 'jobs' in insp.get_table_names()
