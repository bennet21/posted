import os
import subprocess
import pandas as pd

from posted.noslag import DataSet, Mask

def get_git_root():
    """Returns the absolute path of the Git repository root."""
    return subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
    ).stdout.strip()

masks1 = [
    Mask(where={'region': 'Africa'}, use={'source': 'Hatayama10'}),
    Mask(where={'region': 'CIS'}, use={'source': 'Hatayama10'}),
    Mask(where={'region': 'Europe'}, use={'source': 'Cao17'}),
    Mask(where={'region': 'India'}, use={'source': 'Cao21'}),
    Mask(where={'region': 'Iran'}, use={'source': 'Hosseinijou21'}),
    Mask(where={'region': 'Japan', 'end_use': 'Res'}, use={'source': 'Deetman20'}),
    Mask(where={'region': 'Japan', 'end_use': 'NonRes'}, use={'source': 'Cao17'}),
    Mask(where={'region': 'Japan', 'end_use': 'Civ'}, use={'source': 'Cao17'}),
    Mask(where={'region': 'USA'}, use={'source': 'Kapur08'})
]

masks2 = [
    Mask(where={'region': 'China', 'end_use': 'Civ'}, use={'source': 'Cao17'}),
    Mask(where={'region': 'China', 'end_use': 'Res'}, use={'source': 'Cao19'}),
]

masks3 = [
    # South america aggregation causes issues with aggregation as it is only one value.
    # As a workaround, for now we don't specify use_case, even though only Res is available.
    Mask(where={'region': 'Rest of South America'}, use={'source': 'Deetman20'}),
]

teds = DataSet('Buildings and Infrastructure Lifetime')
x = pd.concat([
    teds.aggregate(period=2025, region=["Africa", "CIS", "Europe", "India", "Iran", "Japan", "USA", "Rest of South America"], masks=masks1),
    teds.aggregate(period=2025, region="China", end_use=["Res", "Civ"], masks=masks2),
]).sort_values(by=['end_use', 'time_range', 'region']).reset_index(drop=True)

git_root = os.path.normpath(get_git_root())
git_root_parent = os.path.dirname(git_root)

madrat_output_path = os.path.join(git_root_parent,
                           "madrat_wd", 
                           "sources",
                           "PostedBuiltLifespan",
                           "v1",
                           "buildings_and_infrastructure_lifetime.csv")
local_output_path = os.path.join("lifetime_input",
                                 "output",
                                 "output_buildings_and_infrastructure_lifetime.csv")
x.to_csv(madrat_output_path, index=False)
x.to_csv(local_output_path, index=False)