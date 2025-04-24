import os
import subprocess

from posted.noslag import DataSet

def get_git_root():
    """Returns the absolute path of the Git repository root."""
    return subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
    ).stdout.strip()

teds = DataSet('Buildings and Infrastructure Lifetime')
x = teds.aggregate(period=2025)

git_root = os.path.normpath(get_git_root())
git_root_parent = os.path.dirname(git_root)

madrat_output_path = os.path.join(git_root_parent,
                           "madrat_wd", 
                           "sources",
                           "PostedLifetimes",
                           "v1",
                           "buildings_and_infrastructure_lifetime.csv")
local_output_path = os.path.join("lifetime_input",
                                 "output",
                                 "output_buildings_and_infrastructure_lifetime.csv")
x.to_csv(madrat_output_path, index=False)
x.to_csv(local_output_path, index=False)