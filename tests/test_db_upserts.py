from ytchannelpickcheck.db import connect, init_db


def test_video_upsert(tmp_path):
    db = tmp_path / "a.db"
    init_db(db)
    with connect(db) as conn:
        conn.execute("INSERT OR REPLACE INTO videos(video_id,title) VALUES('v1','t1')")
        conn.execute("INSERT OR REPLACE INTO videos(video_id,title) VALUES('v1','t2')")
        row = conn.execute("SELECT title FROM videos WHERE video_id='v1'").fetchone()
        assert row[0] == "t2"
