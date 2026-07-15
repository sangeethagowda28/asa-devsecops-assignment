from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def search_scans_by_query(db, query: str) -> list:
    # SEC-01 FIX: Use parameterized query with bindparams — user input is NEVER
    # interpolated into the SQL string. The LIKE wildcards are part of the bound
    # value, not the query template, so SQL injection is structurally impossible.
    like_pattern = f"%{query}%"
    sql = text(
        "SELECT id, title, description, severity, status, cve_id, "
        "affected_component, owner_id, created_at FROM scan_results "
        "WHERE title LIKE :pat OR description LIKE :pat OR cve_id LIKE :pat"
    )
    result = db.execute(sql, {"pat": like_pattern})
    return [dict(row._mapping) for row in result]
