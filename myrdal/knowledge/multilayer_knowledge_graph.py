import networkx as nx
from pydantic import BaseModel
from typing import Optional, Any, Dict, List
from sentence_transformers import SentenceTransformer
import numpy as np

class KnowledgeNode(BaseModel):
    id: str
    type: str  # "fact", "concept", "theory", "belief"
    content: str
    timestamp: Optional[str] = None
    source: Optional[str] = None
    confidence: Optional[float] = None
    extra: Optional[Dict[str, Any]] = None
    embedding: Optional[List[float]] = None

class MultiLayerKnowledgeGraph:
    def __init__(self, embedding_model_name="all-MiniLM-L6-v2"):
        self.graph = nx.MultiDiGraph()
        self.embedder = SentenceTransformer(embedding_model_name)

    def add_node(self, node: KnowledgeNode):
        # contentからembeddingを生成
        if node.embedding is None:
            node.embedding = self.embedder.encode(node.content).tolist()
        self.graph.add_node(node.id, **node.dict())

    def add_edge(self, from_id: str, to_id: str, relation: str):
        self.graph.add_edge(from_id, to_id, relation=relation)

    def add_fact(self, content, **kwargs):
        node = KnowledgeNode(id=f"fact_{len(self.graph)}", type="fact", content=content, **kwargs)
        self.add_node(node)
        return node.id

    def add_concept(self, content, **kwargs):
        node = KnowledgeNode(id=f"concept_{len(self.graph)}", type="concept", content=content, **kwargs)
        self.add_node(node)
        return node.id

    def add_theory(self, content, **kwargs):
        node = KnowledgeNode(id=f"theory_{len(self.graph)}", type="theory", content=content, **kwargs)
        self.add_node(node)
        return node.id

    def add_belief(self, content, **kwargs):
        node = KnowledgeNode(id=f"belief_{len(self.graph)}", type="belief", content=content, **kwargs)
        self.add_node(node)
        return node.id

    def query_by_type(self, node_type: str):
        return [n for n, d in self.graph.nodes(data=True) if d.get("type") == node_type]

    def update_knowledge(self, node_id: str, **updates):
        for k, v in updates.items():
            self.graph.nodes[node_id][k] = v

    def auto_update(self, new_content: str, node_type: str = "fact", relation: str = None, parent_id: str = None, **kwargs):
        """
        新しい知識（事実・概念・理論・信念）を自動的に階層構造に統合する。
        parent_idが指定されていれば親ノードとrelationで接続。
        類似ノードがあればマージやリンクも可能（簡易実装）。
        """
        # 既存ノードとベクトル類似度で重複・近似チェック
        similar = self.query_by_vector(new_content, top_k=1)
        if similar and similar[0][1] > 0.95:
            # ほぼ同一知識とみなして既存ノードを更新
            self.update_knowledge(similar[0][0], **kwargs)
            return similar[0][0]
        # 新規ノード追加
        add_func = getattr(self, f"add_{node_type}", self.add_fact)
        new_id = add_func(new_content, **kwargs)
        # 階層リンク
        if parent_id and relation:
            self.add_edge(parent_id, new_id, relation)
        return new_id

    def get_parents(self, node_id: str):
        """上位概念・理論など親ノードを取得"""
        return list(self.graph.predecessors(node_id))

    def get_children(self, node_id: str):
        """下位概念・事実など子ノードを取得"""
        return list(self.graph.successors(node_id))

    def hierarchical_reasoning(self, node_id: str, direction: str = "up", depth: int = 1):
        """
        direction: "up"=親方向, "down"=子方向
        depth: 何階層たどるか
        """
        visited = set()
        frontier = [node_id]
        for _ in range(depth):
            next_frontier = []
            for nid in frontier:
                if direction == "up":
                    parents = self.get_parents(nid)
                    next_frontier.extend(parents)
                else:
                    children = self.get_children(nid)
                    next_frontier.extend(children)
            visited.update(next_frontier)
            frontier = next_frontier
        return list(visited)

    def query_by_vector(self, query_text, top_k=5):
        query_vec = self.embedder.encode(query_text)
        sims = []
        for n, d in self.graph.nodes(data=True):
            node_vec = d.get("embedding")
            if node_vec is not None:
                sim = np.dot(query_vec, node_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(node_vec))
                sims.append((n, sim))
        sims.sort(key=lambda x: x[1], reverse=True)
        return sims[:top_k]

    def visualize(self):
        import matplotlib.pyplot as plt
        pos = nx.spring_layout(self.graph)
        nx.draw(self.graph, pos, with_labels=True)
        plt.show() 