import numpy as np
from pgmpy.readwrite import BIFReader

data_name = "child"
sample_num = 1000

# Load the BIF dataset (e.g., Asia)
reader = BIFReader(f"./BIF/{data_name}.bif")
model = reader.get_model()


# Create adjacency matrix and name list
n = len(model.nodes())
adj_matrix = np.zeros((n, n))
name_list = list(model.nodes())

# Map node names to indices
node_to_idx = {node: idx for idx, node in enumerate(model.nodes())}

# Retrieve edges from the model
edges = model.edges()
for edge in edges:
    i = node_to_idx[edge[0]]
    j = node_to_idx[edge[1]]
    adj_matrix[j][i] = 1

print(adj_matrix)
print(name_list)

sample = model.simulate(n_samples=sample_num)
sample
# Reorder sample columns according to name_list
sample = sample[name_list]
# Convert labels to integer type, starting from 0
for col in sample.columns:
    unique_values = sample[col].unique()
    value_map = {val: idx for idx, val in enumerate(sorted(unique_values))}
    print(value_map)
    sample[col] = sample[col].map(value_map)

# %%
# Save the data to a CSV file
sample.to_csv(f"./{data_name}_{sample_num}_data.csv", index=False)

# Save the adjacency matrix to a CSV file
np.savetxt(
    f"./{data_name}_{sample_num}_GTmatrix.csv", adj_matrix, delimiter=",", fmt="%d"
)
