import os
from pathlib import Path

test_data_dir = Path("/tmp/anime_manager_backend_tests")
os.environ["DATA_DIR"] = str(test_data_dir)
os.environ["DATABASE_URL"] = f"sqlite:///{test_data_dir / 'app.db'}"
