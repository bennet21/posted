from posted.noslag import DataSet
from posted.masking import Mask
import numpy as np


teds = DataSet('Buildings and Infrastructure Lifetime')
teds.normalise()
teds.select(period=2025)
x = teds.aggregate(period=2025)
print(x)