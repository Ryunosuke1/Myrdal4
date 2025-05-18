# Myrdal

## Overview

**Myrdal** is an advanced AI agent framework that integrates multi-layer memory, knowledge synthesis, causal reasoning, metacognition, and Explainable AI (XAI). Built on top of Autogen Agentchat/Core, Myrdal features deliberative AI (CoT/ToT), multi-layer knowledge graphs, self-updating mechanisms, vector search, and a practical chat UI (Flet).

---

## Key Features

### 1. Multi-layer Memory & Knowledge Integration
- **Short-term / Long-term Memory**: Each agent manages its own short-term and long-term memory.
- **MemoryManager**: Centralized management of all agents' memories.

### 2. Knowledge Graph & Vector Search
- **MultiLayerKnowledgeGraph**: Utilizes networkx and sentence-transformers to build a multi-layer knowledge graph, with vector embeddings for each node, enabling fast semantic search (`query_by_vector`).
- **Self-updating & Hierarchical Reasoning**: Supports automatic integration of new knowledge (`auto_update`) and hierarchical reasoning (`hierarchical_reasoning`).

### 3. Knowledge Modules
- **WorldModelNexus (WMN)**: The core module for deliberation, knowledge integration, and self-evaluation. Integrates various knowledge modules (abstract thinking, multilingual understanding, social cognition, knowledge integration, causal reasoning).
- **CausalReasoner**: Causal inference engine based on pgmpy and causal-learn. Supports structure learning, Bayesian network inference, and intervention simulation.
- **ExplainableAI**: Provides explanations for AI decisions using SHAP and LIME.

### 4. Deliberative AI & Metacognition
- **Deliberation Loop**: The AI autonomously calls knowledge modules until it is satisfied, generating final answers and self-evaluations.
- **MetacognitionFramework**: Accepts a dictionary of knowledge modules and allows the LLM to call each module via `call_module` during the deliberation loop.

### 5. Agent Architecture & Collaboration
- **MyrdalAssistantAgent / Verifier**: Two-agent system (assistant and verifier) sharing the same WorldModelNexus instance for consistent and collaborative knowledge integration.
- **SelectorGroupChat**: Supports collaborative dialogue and verification flows among multiple agents.

### 6. UI Integration (Flet)
- **Chat UI**: Intuitive chat UI built with Flet, featuring deliberation process visualization, Markdown support, streaming display, loading indicators, and practical UX enhancements.

---

## Directory Structure

```
myrdal/
  main.py                ... Myrdal core & agent management
  memory/                ... Short/long-term memory, MemoryManager
  knowledge/
    world_model_nexus.py ... WMN core, knowledge integration, deliberation loop
    multilayer_knowledge_graph.py ... Multi-layer knowledge graph, vector search
    knowledge_integration.py ... Knowledge integration module
    abstract_thinking.py ... Abstract thinking module
    multilingual.py      ... Multilingual understanding module
    social_cognition.py  ... Social cognition module
    explainable_ai.py    ... XAI (explainable AI) module
  reasoning/
    causal_reasoner.py   ... Causal reasoning engine
  metacognition/
    metacognition.py     ... Metacognition framework
  agents/
    myrdal_assistant.py  ... Myrdal assistant agent
```

---

## Main Classes & Modules

- **Myrdal** (`main.py`)
  - Entry point for agent, memory, knowledge integration, and dialogue management.

- **WorldModelNexus**
  - Core for deliberation, knowledge integration, and self-evaluation. Integrates all knowledge modules and runs a deliberation loop until the AI is satisfied.

- **MultiLayerKnowledgeGraph**
  - Multi-layer knowledge graph with vector search, self-updating, and hierarchical reasoning.

- **CausalReasoner**
  - Causal inference (structure learning, Bayesian networks, intervention simulation).

- **ExplainableAI**
  - SHAP/LIME-based explanations for AI decisions.

- **MyrdalAssistantAgent / Verifier**
  - Assistant and verifier agents utilizing short-term memory, knowledge modules, and the deliberation loop.

---

## Installation & Usage

(Details to be added)

1. Install required Python packages:
   ```
   pip install -r requirements.txt
   ```

2. Launch the Flet UI:
   ```
   python main.py
   ```

---

## License

(To be specified as needed)

---

## Contribution & Contact

Contributions, bug reports, and feature requests are welcome!
See [CONTRIBUTING.md] or open an issue for details.
