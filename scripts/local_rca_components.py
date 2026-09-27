"""Load unchanged official RCA code with explicit local dependency injection.

The source MODEL string is used only by the original client-dispatch branch.
It is never sent to a provider; the injected client sends the actual Qwen alias.
No OpenAI/config module, credentials, web search or upstream main is imported.
"""
import ast
from typing import Dict, List, Tuple

import numpy as np

from project_paths import SOURCE
from local_re_response import REFormatClient
from setup_graphviz import assert_original_source


def extract(relative, names, namespace=None):
    path = SOURCE / relative
    tree = ast.parse(path.read_text(encoding="utf-8"))
    nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names]
    if {n.name for n in nodes} != set(names):
        raise RuntimeError(f"Official definitions missing: {relative}")
    result = dict(namespace or {})
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), result)
    return result


def official_agent_class(client, *, re_audit):
    import os
    from tqdm import tqdm

    assert_original_source()
    llms = extract("ConstrainAgent/LLMs.py", {"LLMs", "DomainKnowledgeLLM", "ConstrainLLM", "ConstrainReasoningLLM"},
                   {"np": np, "List": List, "Tuple": Tuple})
    original_reasoning = llms["ConstrainReasoningLLM"]

    def reasoning_factory(base, theme, domain_knowledge_dict):
        # ConstrainReasoningLLM explicitly asks <Yes>/<No>; OnlyLLMAgent's
        # earlier smoke test asks lowercase. Preserve each literal; never recase.
        wrapped = REFormatClient(base, expected_guesses=2, audit_callback=re_audit,
                                 terminal_answers=("Yes", "No"))
        return original_reasoning(wrapped, theme, domain_knowledge_dict)

    tree = ast.parse((SOURCE / "config.py").read_text(encoding="utf-8"))
    model = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and
                 any(isinstance(t, ast.Name) and t.id == "MODEL" for t in n.targets))
    if "gpt" not in model:
        raise RuntimeError("Original client-dispatch branch changed; review required")
    def factory(*args, **kwargs):
        return client
    namespace = {**llms, "os": os, "np": np, "tqdm": tqdm, "List": List, "Tuple": Tuple, "Dict": Dict,
                 "MODEL": model, "OPENAI_API_KEY": "unused-local-dispatch",
                 "OpenAIClient": factory, "ConstrainReasoningLLM": reasoning_factory}
    return extract("ConstrainAgent/ConstrainAgent.py", {"ConstrainAgent", "ConstrainNormalAgent"}, namespace)["ConstrainNormalAgent"]


def official_log_summary_call(client, pd):
    import os
    return extract("Log_tools.py", {"generate_log_text", "generate_log_prompt", "generate_pod_summary"},
                   {"os": os, "pd": pd, "OpenAIClient": lambda *a, **kw: client,
                    "OPENAI_API_KEY": "unused-local-dispatch"})


def official_pc():
    from causallearn.graph.GraphClass import CausalGraph
    from causallearn.search.ConstraintBased.PC import pc
    from causallearn.utils.PCUtils.BackgroundKnowledge import BackgroundKnowledge
    return extract("Utils/CausalDiscovery.py", {"cg2matrix", "matrix2backgroundknowledge", "causal_discovery"},
                   {"np": np, "List": List, "CausalGraph": CausalGraph, "pc": pc,
                    "BackgroundKnowledge": BackgroundKnowledge})["causal_discovery"]


def official_visualize():
    import os
    import pydot
    return extract("Utils/visualize.py", {"visualize_graph"},
                   {"os": os, "np": np, "pydot": pydot, "List": List})["visualize_graph"]


def original_dataset_summary(embedding, llm):
    """Preserve released query, reader, splitting, top-k and synthesis defaults.

    Explicitly inject local model dependencies without altering global Settings.
    Source ASTs, including the original strict summary parser, stay unchanged.
    """
    from llama_index.core import SimpleDirectoryReader, StorageContext, VectorStoreIndex, load_index_from_storage

    class LocalIndex:
        def __init__(self, index):
            self.index = index
            self.storage_context = index.storage_context

        def as_query_engine(self):
            return self.index.as_query_engine(llm=llm)

        @staticmethod
        def from_documents(documents):
            return LocalIndex(VectorStoreIndex.from_documents(documents, embed_model=embedding))

    def load(storage_context):
        return LocalIndex(load_index_from_storage(storage_context, embed_model=embedding))

    return extract("Web_tools.py", {"generate_dataset_summary", "split_summary_into_sub_questions"},
                   {"SimpleDirectoryReader": SimpleDirectoryReader, "StorageContext": StorageContext,
                    "VectorStoreIndex": LocalIndex, "load_index_from_storage": load})
