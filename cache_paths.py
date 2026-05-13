from pathlib import Path
from diskcache import Cache

_base = Path(__file__).resolve().parent / ".cache"
domain_classification_cache = Cache(str(_base / "domain_classification_cache"))
topic_dependency_cache = Cache(str(_base / "topic_dependency_cache"))