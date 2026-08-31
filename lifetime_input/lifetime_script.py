import os
import subprocess
import pandas as pd

from posted.noslag import DataSet, Mask

def get_git_root():
    """Returns the absolute path of the Git repository root."""
    return subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
    ).stdout.strip()

masks = [
    Mask(use = {'source': 'Buyle13'}, weight=float('nan'), other=1.0, comment = "case studies"),
    Mask(where={'region': 'China', 'end_use': 'Res'}, use={'source': 'Cao19'}, comment = "time-dependent data"),
]

teds = DataSet('Buildings and Infrastructure Lifetime')
# make sure there are no duplicate entries from one source; otherwise those will be summed.
x = pd.concat([
    teds.aggregate(period=2025, masks=masks),
]).sort_values(by=['end_use', 'time_range', 'region']).reset_index(drop=True)

git_root = os.path.normpath(get_git_root())
git_root_parent = os.path.dirname(git_root)

madrat_output_path = os.path.join(git_root_parent,
                           "madrat_wd", 
                           "sources",
                           "PostedBuiltLifespan",
                           "v20260831",
                           "buildings_and_infrastructure_lifetime.csv")
local_output_path = os.path.join("lifetime_input",
                                 "output",
                                 "output_buildings_and_infrastructure_lifetime.csv")
x.to_csv(madrat_output_path, index=False)
x.to_csv(local_output_path, index=False)