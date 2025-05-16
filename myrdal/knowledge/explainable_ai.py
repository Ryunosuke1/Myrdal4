import shap
import lime.lime_tabular
import numpy as np

class ExplainableAI:
    def __init__(self, model, feature_names=None):
        self.model = model
        self.feature_names = feature_names
    async def shap_explain(self, X):
        explainer = shap.Explainer(self.model)
        shap_values = explainer(X)
        return shap_values
    async def lime_explain(self, X, y=None):
        explainer = lime.lime_tabular.LimeTabularExplainer(
            training_data=np.array(X),
            feature_names=self.feature_names,
            mode="classification"
        )
        exp = explainer.explain_instance(X[0], self.model.predict_proba)
        return exp.as_list() 