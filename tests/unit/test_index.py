from framework_cli.index.db import IndexDB
from framework_cli.index.repository import Repository


def test_index_schema_and_records(tmp_path):
    db = IndexDB(tmp_path / ".framework" / "index.db")
    Repository(db).project("p1", str(tmp_path), "mvp")
    row = db.connection.execute("select profile from projects where id='p1'").fetchone()
    assert row[0] == "mvp"
    assert db.connection.execute("select value from metadata where key='schema_version'").fetchone()[0] == "2"
    assert db.connection.execute("select name from sqlite_master where name='symbol_relations'").fetchone()[0] == "symbol_relations"
    db.close()
