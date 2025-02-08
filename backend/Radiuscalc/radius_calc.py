import pandas as pd
import numpy as np
from scipy.spatial import distance

# Load the data
data = pd.read_csv('../../shop_data.csv')

# User's location
latitude = 20  # Replace with actual latitude
longitude = 45  # Replace with actual longitude
user_location = (latitude, longitude)

# Function to calculate the number of points within a radius for each class
def find_radius(user_location, data, threshold=(5,25)):
    min_radius = 0
    max_radius = 100  # Starting with a high radius, adjust as necessary
    best_radius = None
    best_counts = None

    while min_radius <= max_radius:
        radius = (min_radius + max_radius) / 2
        # Add a column of distance from the user location
        data['distance'] = data.apply(lambda row: distance.euclidean((row['x'], row['y']), user_location), axis=1)
        # Filter data within the current radius and store in a df called within_radius
        within_radius = data[data['distance'] <= radius]
        within_radius = within_radius.sort_values(by='distance').reset_index(drop=True)
        # print(within_radius)
        # break 
        class_counts = within_radius['shop_type'].value_counts()
        print(class_counts)
        print(radius)
        # break
    #    IF class counts are outside the    threshold, adjust the radius increase radius if counsts is low and increase radius is count is more
        if class_counts.min() < threshold[0]:
            min_radius = radius + 1
        elif class_counts.max() > threshold[1]:
            max_radius = radius - 1
        else:
            best_radius = radius
            best_counts = class_counts
            break
    return best_radius, best_counts

# Example usage
radius, counts = find_radius(user_location, data)

if radius is not None:
    print(f"Best radius: {radius}")
    print(f"Counts within radius: {counts}")

    # PLot all points in the csv and also plot thef fixed point and draw a circle with the radius
    import matplotlib.pyplot as plt
    plt.figure(figsize=(10, 10))
    shop_types = data['shop_type'].unique()
    colors = plt.cm.get_cmap('tab20', len(shop_types))

    for i, shop_type in enumerate(shop_types):
        shop_data = data[data['shop_type'] == shop_type]
        plt.scatter(shop_data['x'], shop_data['y'], c=[colors(i)[:3]], label=shop_type)  # Use RGB values
    plt.scatter(user_location[0], user_location[1], c='black', marker="x", label='User Location')
    circle = plt.Circle(user_location, radius, color='green', fill=False, label='Radius')
    plt.gca().add_artist(circle)
    plt.show()

else:
    print("No suitable radius found within the threshold.")