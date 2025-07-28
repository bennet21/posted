# %%
from pathlib import Path
import pandas as pd

from posted.noslag import DataSet

# %% 

# %%

posted_filename = "Cement Production"
posted_filename = "Iron Direct Reduction"
posted_parent_variable = f"Tech|{posted_filename}"
teds = DataSet(posted_parent_variable)
df_posted = teds.aggregate(region="World", period=2019, drop_singular_fields=True) 

# %%
# translate Posted file names to CaCoCa file names
file_map = {
    "Cement Production": "cement",
    "Iron Direct Reduction": "steel_dri",
}
# code folder differs if run by ipython or debugger
code_folder = Path.cwd().parent if Path.cwd().name == "posted" else Path.cwd().parent.parent
target_folder = code_folder / "cacoca" / "data" / "tech" / "basic"
df_cacoca_path = target_folder / f"{file_map[posted_filename]}.csv"
df_cacoca = pd.read_csv(df_cacoca_path, dtype={"Period": "Int64"})

# %%
# Posted variable translation to CaCoCa Type and Component
energy_types = ["Electricity", "Coal", "Natural Gas"]
translation = {"Fossil Gas": "Natural Gas"}

def variable_translation(variable, parent_variable):
    # remove parent variable prefix
    variable = variable.replace(f"{parent_variable}|", "")

    # split variable by "|"
    if "|" in variable:
        type_, component = variable.split("|", 1)
    else:
        type_ = variable
        component = variable

    if type_ == "CAPEX":
        type_ = "High CAPEX"

    if type_ == "OPEX Variable" or type_ == "OPEX Fixed":
        type_ = "OPEX"
        component = "Additional OPEX"

    if type_ ==  "Input":
        if component in energy_types:
            type_ = "Energy demand"
        else:
            # I have never seen this in CaCoCa
            type_ = "Feedstock demand"
        
    component = translation.get(component, component)
    
    return {"Type": type_, "Component": component}
            
variable_extraction = df_posted["variable"].apply(lambda v: variable_translation(v, posted_parent_variable))
type_list = [d["Type"] for d in variable_extraction]
component_list = [d["Component"] for d in variable_extraction]

# translate Posted columns to CaCoCa columns
df_translated = pd.DataFrame({
    # "Technology": df_posted["subtech"].apply(lambda x: f"Posted-{x}"),
    "Technology": df_posted["mode"].apply(lambda x: f"Posted-DRI-{x}"),
    "Mode": None,
    "Type": type_list,
    "Component": component_list,
    "Subcomponent": None,
    "Region": df_posted["region"],
    "Period": df_posted["period"],
    "Usage": None,
    "Value": df_posted["value"],
    "Uncertainty": None,
    "Unit": df_posted["unit"],
    "Non-unit conversion factor": None,
    "Value and uncertainty comment": None,
    "Source reference": "Posted {posted_parent_variable}",
    "Source comment": None,
})

# %%
# Get allowed types and components from df_cacoca
allowed_types = set(df_cacoca["Type"].dropna().unique())
allowed_components = set(df_cacoca["Component"].dropna().unique())

component_exceptions = {"Coal"}
allowed_components.update(component_exceptions)

# Find rows in df_translated with new types/components
mask_type = df_translated["Type"].isin(allowed_types)
mask_component = df_translated["Component"].isin(allowed_components)
mask_valid = mask_type & mask_component

# Warn about dropped rows
# Warn about dropped rows (unique combinations only)
dropped_rows = df_translated[~mask_valid]
if not dropped_rows.empty:
    unique_dropped = dropped_rows[["Type", "Component"]].drop_duplicates()
    print("Warning: The following unique Type/Component combinations will be dropped:")
    print(unique_dropped)

# Keep only valid rows
df_translated_valid = df_translated[mask_valid]

# Concatenate
# %%
df_cacoca_new = pd.concat([df_cacoca, df_translated_valid], ignore_index=True)
df_cacoca_new.to_csv(df_cacoca_path, index=False)

# Coupling Goal: extract
# cost variables CAPEX, OPEX,
# 5 different energy types: electricity, gas, coal, oil, h2 (to be converted to emissions)
# process emissions

# Questions for coupling:
# OPEX: components need to be added up (Q: in POSTED or CaCoCa?), Using agg=, I get weird stuff
# Not all inputs are always given - are they implicitly zero? 
    # Meistens ja, aber manche Quellen reporten nicht alles, wird dann bei aggregate() weggelassen
    # (auch wenn all anderen Quellen etwas reporten - der unterschied ist quasi fill nan mit zero oder weglassen
# What to do with feedstock input/output?
    # Inputs sind generell nicht in OPEX enthalten --> müssen über Input Preis in OPEX umgerechnet werden
# Are Emissions only process emissions and other emissions need to be calculated by emission factor?
# What is input Heat - where does it come from?

# Technical questions:
# Where are the conversions between units defined?
# Is it inteded that I have to provide a region if region = * everywhere?
# Why does extrapolate_period not change anything?


# %%
