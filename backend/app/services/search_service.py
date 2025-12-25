import torch
from sentence_transformers import SentenceTransformer, util
from app.models.problem import Problem
from app.models.user import db

class SearchService:
    def __init__(self):
        self.model = None
        self.problems_cache = {}
        self.embeddings = None
        self.index_to_id = []

    def _ensure_model_loaded(self):
        if self.model is None:
            # Using BAAI/bge-small-zh-v1.5 for Chinese semantic search
            self.model = SentenceTransformer('BAAI/bge-small-zh-v1.5')

    def rebuild_index(self):
        self._ensure_model_loaded()
        problems = Problem.query.all()
        if not problems:
            self.embeddings = None
            self.index_to_id = []
            self.problems_cache = {}
            return

        self.problems_cache = {
            p.id: {
                "id": p.id,
                "title": p.title,
                "content": p.content,
                "type": p.type,
                "language": p.language,
                "time_limit": p.time_limit,
                "memory_limit": p.memory_limit
            } for p in problems
        }
        self.index_to_id = list(self.problems_cache.keys())

        texts = [f"题目: {p['title']}。描述: {p['content']}" for p in self.problems_cache.values()]
        self.embeddings = self.model.encode(texts, convert_to_tensor=True)

    def search(self, query, top_k=5):
        if self.embeddings is None:
            self.rebuild_index()

        if self.embeddings is None:
            return []

        self._ensure_model_loaded()
        # BGE model retrieval instruction
        query_embedding = self.model.encode(f"查询: {query}", convert_to_tensor=True)
        cos_scores = util.cos_sim(query_embedding, self.embeddings)[0]

        actual_k = min(top_k, len(self.index_to_id))
        top_results = torch.topk(cos_scores, k=actual_k)

        results = []
        for score, idx in zip(top_results[0], top_results[1]):
            pid = self.index_to_id[idx.item()]
            prob = self.problems_cache[pid]
            results.append({
                **prob,
                "score": float(score)
            })
        return results

search_service = SearchService()
