import numpy as np
import pandas as pd


#  the Points P1 and P2 are latitude and longitude coordinates
def distance(p1, p2):
    return np.linalg.norm(p1 - p2)
