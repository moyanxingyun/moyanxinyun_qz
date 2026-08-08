# -*- coding: utf-8 -*-
"""本地数据存储：SQLite 单表存储，按 id 去重，支持种子导入与手动录入。"""
import datetime
import json
import pathlib
import sqlite3

ROOT = pathlib.Path(__file__).resolve().parent
DB = ROOT / "data.db"


def connect():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init():
    conn = connect()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS records(
          id TEXT PRIMARY KEY,
          kind TEXT NOT NULL,
          data TEXT NOT NULL,
          source TEXT,
          updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS crawl_log(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          company TEXT,
          url TEXT,
          status TEXT,
          note TEXT,
          fetched_at TEXT
        );
        """
    )
    conn.commit()
    conn.close()


def upsert(rows):
    """rows: iterable of (kind, record_dict)"""
    conn = connect()
    now = datetime.datetime.now().isoformat(timespec="seconds")
    for kind, rec in rows:
        conn.execute(
            """INSERT INTO records(id, kind, data, source, updated_at)
               VALUES(?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET
                 kind=excluded.kind,
                 data=excluded.data,
                 source=excluded.source,
                 updated_at=excluded.updated_at""",
            (
                rec["id"],
                kind,
                json.dumps(rec, ensure_ascii=False),
                rec.get("source", "人工录入"),
                now,
            ),
        )
    conn.commit()
    conn.close()


def load_all(kind):
    conn = connect()
    rows = conn.execute(
        "SELECT data, source, updated_at FROM records WHERE kind=?", (kind,)
    ).fetchall()
    conn.close()
    out = []
    for r in rows:
        d = json.loads(r["data"])
        d["_source"] = r["source"]
        d["_updated_at"] = r["updated_at"]
        out.append(d)
    return out


def delete_by_company(company):
    """删除某公司的全部记录（采集到官网真实数据后接管该公司）。"""
    conn = connect()
    rows = conn.execute("SELECT id, data FROM records").fetchall()
    for r in rows:
        try:
            d = json.loads(r["data"])
        except json.JSONDecodeError:
            continue
        if d.get("company") == company:
            conn.execute("DELETE FROM records WHERE id=?", (r["id"],))
    conn.commit()
    conn.close()


def log_crawl(company, url, status, note):
    conn = connect()
    conn.execute(
        "INSERT INTO crawl_log(company,url,status,note,fetched_at) VALUES(?,?,?,?,?)",
        (company, url, status, note, datetime.datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()


def latest_update():
    conn = connect()
    row = conn.execute("SELECT MAX(updated_at) AS u FROM records").fetchone()
    conn.close()
    return row["u"]
