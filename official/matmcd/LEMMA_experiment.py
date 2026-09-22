from ConstrainAgent.ConstrainAgent import ConstrainNormalAgent
from Utils.CausalDiscovery import (
    causal_discovery,
)
from Utils.data import load_Lemma_data
from Utils.visualize import visualize_graph
from Utils.RCA import random_walk_with_restart
from Web_tools import (
    split_summary_into_sub_questions,
    collect_web_content,
    generate_dataset_summary,
)

causal_discovery_algorithm = "pc"
# causal_discovery_algorithm = "Exact-Search"
# causal_discovery_algorithm = "DirectLiNGAM"

system_name = "Product_Review"
theme = "MicroService system about Product Review"
day = 20210517

# system_name = "Cloud_Computing"
# theme = "MicroService system about Cloud Computing"
# day = 20231207


print(f"Loading dataset: {system_name}_{day}...")
data_table, log_dir = load_Lemma_data(system_name, day)

data = data_table.values
labels = data_table.columns.tolist()


print(f"Running {causal_discovery_algorithm} algorithm...")
adjacency_matrix = causal_discovery(data, labels, method=causal_discovery_algorithm)
visualize_graph(adjacency_matrix, labels, f"./image/{system_name}_{day}/PC_graph.png")
count = random_walk_with_restart(adjacency_matrix, len(labels) - 1)
count_label_pairs = list(zip(count, labels))
sorted_pairs = sorted(count_label_pairs, key=lambda x: x[0], reverse=True)
print("\nRanked metrics by importance:")
for count, label in sorted_pairs:
    print(f"{label}: {count:.4f}")
print("================================================\n")


print("Running ConstrainAgent...")
constrain_agent = ConstrainNormalAgent(
    labels,
    theme,
    graph_matrix=adjacency_matrix,
    causal_discovery_algorithm=causal_discovery_algorithm,
    use_reasoning=False,
)

constraint_matrix = constrain_agent.run(
    use_cache=False,
    cache_path=f"./cache/Domain_knowledge/{system_name}_{day}/{causal_discovery_algorithm}",
)

adjacency_matrix_optimized = causal_discovery(
    data,
    labels,
    method=causal_discovery_algorithm,
    constraint_matrix=constraint_matrix,
)
visualize_graph(
    adjacency_matrix_optimized,
    labels,
    f"./image/{system_name}_{day}/PC_graph_Optimized.png",
)

count = random_walk_with_restart(adjacency_matrix, len(labels) - 1)
count_label_pairs = list(zip(count, labels))
sorted_pairs = sorted(count_label_pairs, key=lambda x: x[0], reverse=True)
print("\nRanked metrics by importance:")
for count, label in sorted_pairs:
    print(f"{label}: {count:.4f}")
print("================================================\n")

print("Running ConstrainAgent with web information...")
# data_info, node_info = split_summary_into_sub_questions(
#     open(f"./cache/Summarized_info/{system_name}_{day}_info.txt").read()
# )

collect_web_content(system_name, labels, loop_num=5, use_tavily=False)
data_info, node_info = split_summary_into_sub_questions(
    generate_dataset_summary(
        system_name,
        labels,
        output_dir="./cache/Summarized_info",
        embeddings_path="./cache/RAG_Database/Embeddings",
        save_embeddings=True,
    )
)


print(data_info)
print(node_info)

constrain_agent = ConstrainNormalAgent(
    labels,
    theme,
    graph_matrix=adjacency_matrix,
    causal_discovery_algorithm=causal_discovery_algorithm,
    dataset_information=data_info,
    node_information=node_info,
    use_reasoning=False,
)

prompt, system_prompt = constrain_agent.domain_knowledge_LLM.generate_prompt(
    0, 1, node_info
)

constraint_matrix = constrain_agent.run(
    use_cache=False,
    cache_path=f"./cache/Domain_knowledge/{system_name}_{day}/{causal_discovery_algorithm}",
)

adjacency_matrix_optimized = causal_discovery(
    data,
    labels,
    method=causal_discovery_algorithm,
    constraint_matrix=constraint_matrix,
)
visualize_graph(
    adjacency_matrix_optimized,
    labels,
    f"./image/{system_name}_{day}/PC_graph_Optimized_web.png",
)

count = random_walk_with_restart(adjacency_matrix_optimized, len(labels) - 1)
count_label_pairs = list(zip(count, labels))
sorted_pairs = sorted(count_label_pairs, key=lambda x: x[0], reverse=True)
print("\nRanked metrics by importance:")
for count, label in sorted_pairs:
    print(f"{label}: {count:.4f}")
print("================================================\n")

print("Running ConstrainAgent with web information with Reasoning...")
data_info, node_info = split_summary_into_sub_questions(
    open(f"./cache/Summarized_info/{system_name}_{day}_info.txt").read()
)

print(data_info)
print(node_info)

constrain_agent = ConstrainNormalAgent(
    labels,
    theme,
    graph_matrix=adjacency_matrix,
    causal_discovery_algorithm=causal_discovery_algorithm,
    dataset_information=data_info,
    node_information=node_info,
    use_reasoning=True,
)

prompt, system_prompt = constrain_agent.domain_knowledge_LLM.generate_prompt(
    0, 1, node_info
)

constraint_matrix = constrain_agent.run(
    use_cache=False,
    cache_path=f"./cache/Domain_knowledge/{system_name}_{day}/{causal_discovery_algorithm}",
)

adjacency_matrix_optimized = causal_discovery(
    data,
    labels,
    method=causal_discovery_algorithm,
    constraint_matrix=constraint_matrix,
)
visualize_graph(
    adjacency_matrix_optimized,
    labels,
    f"./image/{system_name}_{day}/PC_graph_Optimized_web.png",
)

count = random_walk_with_restart(adjacency_matrix_optimized, len(labels) - 1)
count_label_pairs = list(zip(count, labels))
sorted_pairs = sorted(count_label_pairs, key=lambda x: x[0], reverse=True)
print("\nRanked metrics by importance:")
for count, label in sorted_pairs:
    print(f"{label}: {count:.4f}")
print("================================================\n")
