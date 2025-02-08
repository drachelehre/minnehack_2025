import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# World size is 100x100
# Create 50 random points for each of 3 classes with 2 sepeate clusters

# np.random.seed(0)
N_Types = 3
N_clusters = 2

for shop_type in range(N_Types):
    # Create 2 gaussian clusters for each shop type with 60% and 40% of the points
    for cluster in range(N_clusters):
        N_points = 50
        if cluster == 0:
            N_points = 30
        #  The Cluster Centers need to spread randomly
        center = np.random.rand(2) * 100
        #  The Cluster Spread needs to be random
        spread = np.random.rand(2) * 50
        x = np.random.normal(center[0], spread[0], N_points)
        y = np.random.normal(center[1], spread[1], N_points)
        
        plt.scatter(x, y,color = ['red', 'green', 'blue'][shop_type])
        
        #  Save the data to a csv file
        data = pd.DataFrame({'x': x, 'y': y, 'shop_type': shop_type})
        data.to_csv(f"shop_data.csv", index=False)
        
plt.savefig("shop_data.png")        
plt.show()

