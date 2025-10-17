# %%
# IMPORTS

from pathlib import Path
import pandas as pd

from posted.noslag import DataSet

# %%
# READ POSTED DATA

posted_filename = "Cement Production"
# posted_filename = "Iron Direct Reduction"
# posted_filename = "Electrolysis"
posted_parent_variable = f"Tech|{posted_filename}"
teds = DataSet(posted_parent_variable)
df_posted = teds.aggregate(region="World", period=2025) 
df_posted.drop(columns=["region"], inplace=True) # region is redundant
df_posted

# %%
# CONVERT POSTED TO CACOCA FORMAT

# Posted variable translation to CaCoCa Type and Component
# TODO fill
energy_types = ["Electricity", "Coal", "Natural Gas"]
feedstock_types = ["Oxygen", "Iron Ore", "Scrap Steel"]
emission_types = ["CO2"]
translation = {"Fossil Gas": "Natural Gas"} #TODO fill
posted_opex_components = ['OPEX Variable', 'OPEX Fixed']

def variable_translation(variable: str, parent_variable: str):
    """Translate Posted variable to CaCoCa Type and Component."""

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

    elif type_ in posted_opex_components:
        component = type_ # variable and fixed opex will later be combined to additional opex
        type_ = "OPEX"
    
    elif type_ ==  "Input":
        if component in energy_types:
            type_ = "Energy demand"
        elif component in feedstock_types:
            type_ = "Feedstock demand"
        else:
            raise ValueError(f"Unknown component {component} for Input variable")

    component = translation.get(component, component)
    
    return {"Type": type_, "Component": component}
            
variable_extraction = df_posted["variable"].apply(lambda v: variable_translation(v, posted_parent_variable))
type_list = [d["Type"] for d in variable_extraction]
component_list = [d["Component"] for d in variable_extraction]

# translate Posted columns to CaCoCa columns
df_cacoca = pd.DataFrame({
    "Technology": df_posted["subtech"],
    "Mode": None, #that's ok
    "Type": type_list,
    "Component": component_list,
    "Subcomponent": None, # that's ok
    "Region": None, #that's ok
    "Period": df_posted["period"],
    "Usage": None, #that's ok
    "Value": df_posted["value"],
    "Uncertainty": None, #that's ok
    "Unit": df_posted["unit"], # ok
    "Non-unit conversion factor": None, # ok
    "Value and uncertainty comment": None, # ok
    "Source reference": f"Posted {posted_parent_variable}",
    "Source comment": None, #ok
})

# %%
# ADD OPEX COMPONENTS
# TODO Warning: This assumes OPEX and CAPEX have compatible unit!
is_opex_mask = df_cacoca['Component'].isin(posted_opex_components)
df_opex = df_cacoca[is_opex_mask].copy()
df_other = df_cacoca[~is_opex_mask]

if not df_opex.empty:
    # sort (as OPEX Variable should be the master for other columns): 
    df_opex['Component'] = pd.Categorical(df_opex['Component'], categories=posted_opex_components, ordered=True)
    df_opex = df_opex.sort_values("Component")

    # aggregate OPEX components
    grouping_cols = [col for col in df_cacoca.columns if col not in ['Component', 'Value', 'Unit']]
    agg_logic = {'Value': 'sum', 'Unit': 'first'}
    aggregated_opex = df_opex.groupby(grouping_cols, as_index=False, dropna=False).agg(agg_logic)
    aggregated_opex['Component'] = 'Additional OPEX'

    # add aggregated OPEX back to CaCoCa dataframe
    df_cacoca = pd.concat([df_other, aggregated_opex], ignore_index=True)



# %%
# FILTER UNWANTED ENTRIES

# TODO fill
allowed_types = {
    "High CAPEX",
    "Low CAPEX",
    "Energy demand",
    "Feedstock demand",
    "OPEX",
    "Emissions"
}
allowed_components = {
    "CAPEX",
    "Additional OPEX",
}
allowed_components.update(energy_types, feedstock_types, emission_types)

# Find rows in df_translated with new types/components
mask_type = df_cacoca["Type"].isin(allowed_types)
mask_component = df_cacoca["Component"].isin(allowed_components)
mask_valid = mask_type & mask_component

expected_removal_types = {
    # specified in project description
    "Lifetime",
    "OCF",
    "Output Capacity",
    "Output",
}

# Warn about dropped rows
dropped_rows = df_cacoca[~mask_valid]
unexpected_dropped = dropped_rows[~dropped_rows["Type"].isin(expected_removal_types)]
if not unexpected_dropped.empty:
    unique_dropped = unexpected_dropped[["Type", "Component"]].drop_duplicates()
    print("Warning: Unexpected unique Type/Component combinations are dropped:")
    print(unique_dropped)

# TODO add low capex
# TODO get emissions via emissions factor


# Keep only valid rows
df_cacoca = df_cacoca[mask_valid]

# %%
# SAVE CACOCA DATAFRAME TO CSV

code_folder = Path.cwd().parent if Path.cwd().name == "posted" else Path.cwd().parent.parent
target_folder = code_folder / "cacoca" / "data" / "tech" / "posted"

# ensure target folder exists
target_folder.mkdir(parents=True, exist_ok=True)

df_cacoca_path = target_folder / f"{posted_filename}.csv"
df_cacoca.to_csv(df_cacoca_path, index=False)

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
