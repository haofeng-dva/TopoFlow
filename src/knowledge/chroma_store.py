"""工业标准与成功/失败案例知识库。"""

import hashlib
import json
from pathlib import Path
from typing import Optional


def _vectorize(payload: dict, dimensions: int = 16) -> list[float]:
    vector = [0.0] * dimensions
    for key, value in sorted(payload.items()):
        token = f"{key}={value}".encode("utf-8")
        digest = hashlib.sha256(token).digest()
        index = digest[0] % dimensions
        if isinstance(value, (int, float)):
            magnitude = float(value) / (abs(float(value)) + 1.0)
        else:
            magnitude = (digest[1] / 127.5) - 1.0
        vector[index] += magnitude
    norm = sum(item * item for item in vector) ** 0.5 or 1.0
    return [item / norm for item in vector]


class KnowledgeStore:
    """优先使用 ChromaDB，失败时退回本地 JSONL。"""

    def __init__(self, persist_dir: str = "./knowledge_base"):
        self.persist_dir = Path(persist_dir).expanduser().resolve()
        self.ready = False
        self.collection = None
        self.fallback_path = self.persist_dir / "cases.jsonl"

    def initialize(self):
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        try:
            import chromadb
            client = chromadb.PersistentClient(path=str(self.persist_dir))
            self.collection = client.get_or_create_collection(
                name="topoflow_cases", metadata={"hnsw:space": "cosine"}
            )
        except Exception:
            self.collection = None
            self.fallback_path.touch(exist_ok=True)
        self.ready = True
        return self

    def _ensure_ready(self):
        if not self.ready:
            self.initialize()

    def retrieve_similar(self, query: dict, top_k: int = 3) -> list:
        self._ensure_ready()
        if self.collection is not None:
            result = self.collection.query(
                query_embeddings=[_vectorize(query)],
                n_results=max(1, top_k),
                include=["metadatas", "documents", "distances"],
            )
            cases = []
            for index, metadata in enumerate(result.get("metadatas", [[]])[0]):
                document = result.get("documents", [[]])[0][index]
                cases.append({
                    **json.loads(document),
                    "metadata": metadata,
                    "distance": result.get("distances", [[]])[0][index],
                })
            return cases

        cases = self._fallback_cases()
        query_vector = _vectorize(query)
        def distance(case):
            candidate = _vectorize(case.get("features", {}))
            return 1.0 - sum(a * b for a, b in zip(query_vector, candidate))
        return sorted(cases, key=distance)[:top_k]

    def _record(self, case: dict):
        self._ensure_ready()
        case_id = case["case_id"]
        if self.collection is not None:
            self.collection.upsert(
                ids=[case_id],
                embeddings=[_vectorize(case.get("features", {}))],
                documents=[json.dumps(case, ensure_ascii=False)],
                metadatas=[{"outcome": case["outcome"], "failed_gate": case.get("failed_gate", "")}],
            )
            return
        with self.fallback_path.open("a", encoding="utf-8") as output:
            output.write(json.dumps(case, ensure_ascii=False) + "\n")

    def record_success(self, task_id: str, strategy: dict, metrics: dict):
        self._record({
            "case_id": f"{task_id}:success",
            "task_id": task_id,
            "outcome": "success",
            "features": strategy,
            "strategy": strategy,
            "metrics": metrics,
        })

    def record_failure(self, task_id: str, strategy: dict, failed_gate: str, metrics: dict):
        self._record({
            "case_id": f"{task_id}:failure:{failed_gate}",
            "task_id": task_id,
            "outcome": "failure",
            "failed_gate": failed_gate,
            "features": strategy,
            "strategy": strategy,
            "metrics": metrics,
        })

    def _fallback_cases(self) -> list:
        if not self.fallback_path.is_file():
            return []
        cases = []
        for line in self.fallback_path.read_text(encoding="utf-8").splitlines():
            try:
                cases.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return cases

    def get_failure_count(self, pattern: dict) -> int:
        return sum(
            1 for case in self.retrieve_similar(pattern, top_k=100)
            if case.get("outcome") == "failure" and all(
                case.get("features", {}).get(key) == value for key, value in pattern.items()
            )
        )
