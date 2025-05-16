# 知識グラフ（例: Neo4j, NetworkX等）

import networkx as nx

class KnowledgeGraph:
    def __init__(self):
        self.graph = nx.MultiDiGraph()
    async def add_fact(self, subject, predicate, obj):
        self.graph.add_edge(subject, obj, key=predicate)
    async def query(self, subject=None, predicate=None, obj=None):
        results = []
        for u, v, k in self.graph.edges(keys=True):
            if (subject is None or u == subject) and (predicate is None or k == predicate) and (obj is None or v == obj):
                results.append((u, k, v))
        return results
    async def delete_fact(self, subject, predicate, obj):
        self.graph.remove_edge(subject, obj, key=predicate) 