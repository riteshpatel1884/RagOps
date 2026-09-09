import os
import tempfile

# Must run before any `app.*` module is imported (conftest.py loads first),
# since app.core.config.Settings() reads these at first access and is
# lru_cached after that. Lets the whole suite run with zero external
# services: no Postgres, no Qdrant server, no Groq key required.
_tmp_dir = tempfile.mkdtemp(prefix="ragops_test_")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_tmp_dir}/test.db")
os.environ.setdefault("QDRANT_PATH", os.path.join(_tmp_dir, "qdrant_data"))
os.environ.setdefault("QDRANT_URL", "")
os.environ.setdefault("QDRANT_API_KEY", "")
os.environ.setdefault("GROQ_API_KEY", "")
os.environ.setdefault("UPLOAD_DIR", os.path.join(_tmp_dir, "uploads"))
