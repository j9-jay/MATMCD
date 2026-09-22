import numpy as np


def random_walk_with_restart(
    Q: np.ndarray, start: int, steps: int = 1000, rp: float = 0.05, max_self: int = 10
) -> np.ndarray:
    # Convert -1 and 2 to 1 in both directions
    Q = Q.copy()  # Create a copy to avoid modifying the original matrix
    for i in range(Q.shape[0]):
        for j in range(Q.shape[1]):
            if Q[i, j] in [-1, 2]:
                Q[i, j] = 1
                Q[j, i] = 1
    Q[-1, :] = Q[:, -1] = np.minimum(Q[-1, :] + Q[:, -1], 1)

    Q[Q > 1] = 1.0
    n = Q.shape[0]
    count = np.zeros(n)
    current = start
    self_visit = 0
    for step in range(steps):
        if np.random.rand() > rp:
            prob = Q[current, :].astype(float)  # Convert to float for division
            psum = prob.sum()
            if psum == 0:
                current = start
            else:
                prob = prob / psum  # Division will now work with float array
                next = np.random.choice(n, 1, p=prob)[0]
                if next == current:
                    self_visit += 1
                    if self_visit == max_self:
                        current = start
                        self_visit = 0
                        continue
                current = next
                count[current] += 1
        else:
            current = start
    return count
