# 因果推論エンジン（pgmpy/causal-learnベース）

import pandas as pd
import networkx as nx
from pgmpy.estimators import PC, HillClimbSearch, BIC, BayesianEstimator
from pgmpy.models import BayesianNetwork
from pgmpy.inference import VariableElimination
from causallearn.search.ConstraintBased.PC import pc
from causallearn.utils.GraphUtils import GraphUtils

class CausalReasoner:
    def __init__(self):
        self.graph = None  # networkx.DiGraph
        self.model = None  # pgmpy.models.BayesianNetwork
        self.data = None

    async def discover_structure(self, data: pd.DataFrame, method: str = "pc", **kwargs):
        self.data = data
        if method == "pc":
            # causal-learnのPCアルゴリズム
            cg = pc(data.values, node_names=list(data.columns))
            self.graph = GraphUtils.to_nx_graph(cg.G, labels=list(data.columns))
        elif method == "hillclimb":
            # pgmpyのHillClimbSearch
            hc = HillClimbSearch(data)
            best_model = hc.estimate(scoring_method=BIC(data))
            self.graph = best_model
        else:
            raise ValueError(f"Unknown structure learning method: {method}")
        return self.graph

    async def fit_bayesian_network(self):
        if self.graph is None:
            raise ValueError("Graph not set. Run discover_structure first.")
        if isinstance(self.graph, nx.DiGraph):
            edges = list(self.graph.edges())
            model = BayesianNetwork(edges)
        else:
            model = BayesianNetwork(self.graph.edges())
        model.fit(self.data, estimator=BayesianEstimator, prior_type="BDeu")
        self.model = model
        return model

    async def estimate_effect(self, treatment: str, outcome: str, intervention_value=1):
        if self.model is None:
            await self.fit_bayesian_network()
        infer = VariableElimination(self.model)
        # 介入: do(treatment=intervention_value)
        # P(outcome | do(treatment=intervention_value))
        q = infer.query(variables=[outcome], do={treatment: intervention_value})
        return q

    async def simulate_intervention(self, intervention: dict):
        if self.model is None:
            await self.fit_bayesian_network()
        infer = VariableElimination(self.model)
        q = infer.query(variables=list(self.data.columns), do=intervention)
        return q

    async def plot(self, filename="causal_graph.png"):
        import matplotlib.pyplot as plt
        if self.graph is not None:
            nx.draw(self.graph, with_labels=True, node_color='lightblue', edge_color='gray')
            plt.savefig(filename)
            plt.close()

    async def infer(self, query: dict):
        if self.model is None:
            await self.fit_bayesian_network()
        infer = VariableElimination(self.model)
        q = infer.query(**query)
        return q

    async def __call__(self, **kwargs):
        method = kwargs.get("method", "infer")
        # グラフ未セット時はLLMにdiscover_structureを促す返答を返す
        if self.graph is None and method != "discover_structure":
            # ここでデータの例や説明を返すことも可能
            return {
                "thought": "Causal graph is not set. Please call 'discover_structure' with appropriate data before running inference.",
                "call_module": "causal_reasoner",
                "call_args": {"method": "discover_structure", "data": "<your_dataframe_here>"},
                "satisfied": False,
                "final_answer": None
            }
        if method == "infer":
            query = kwargs.get("query", {})
            return {"causal_inference": await self.infer(query)}
        elif method == "estimate_effect":
            treatment = kwargs.get("treatment")
            outcome = kwargs.get("outcome")
            intervention_value = kwargs.get("intervention_value", 1)
            return {"effect": await self.estimate_effect(treatment, outcome, intervention_value)}
        elif method == "simulate_intervention":
            intervention = kwargs.get("intervention", {})
            return {"simulation": await self.simulate_intervention(intervention)}
        elif method == "discover_structure":
            data = kwargs.get("data")
            if data is None:
                return {"error": "No data provided for structure discovery."}
            return {"graph": await self.discover_structure(data)}
        return {"causal_inference": "因果推論結果"} 