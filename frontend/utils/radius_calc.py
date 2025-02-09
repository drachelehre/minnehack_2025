import pandas as pd
import numpy as np
from scipy.spatial import distance

# Load the data

# Function to calculate the number of points within a radius for each class
def find_radius(user_location, data, threshold=16):
    req_counts = threshold
    #  select top req_counts for each type of shop
    shop_types = data['type'].unique()
    
    new_data = pd.DataFrame(columns=data.columns)
    for shop_type in shop_types:
        shop_data = data[data['type'] == shop_type]
        shop_data = shop_data.sort_values(by='distance')
        new_data = pd.concat([new_data, shop_data.head(req_counts)], ignore_index=True)
        
    best_radius = new_data['distance'].max()
    best_counts = new_data['type'].value_counts()
    new_data = new_data.reset_index(drop=True)
            
            
    return best_radius, best_counts, new_data

# # Example usage
# radius, counts = find_radius(user_location, data)

# if radius is not None:
#     print(f"Best radius: {radius}")
#     print(f"Counts within radius: {counts}")

#     # PLot all points in the csv and also plot thef fixed point and draw a circle with the radius
#     import matplotlib.pyplot as plt
#     plt.figure(figsize=(10, 10))
#     shop_types = data['shop_type'].unique()
#     colors = plt.cm.get_cmap('tab20', len(shop_types))

#     for i, shop_type in enumerate(shop_types):
#         shop_data = data[data['shop_type'] == shop_type]
#         plt.scatter(shop_data['x'], shop_data['y'], c=[colors(i)[:3]], label=shop_type)  # Use RGB values
#     plt.scatter(user_location[0], user_location[1], c='black', marker="x", label='User Location')
#     circle = plt.Circle(user_location, radius, color='green', fill=False, label='Radius')
#     plt.gca().add_artist(circle)
#     plt.show()

# else:
#     print("No suitable radius found within the threshold.")