import pandas as pd
from pathlib import Path

from posted.noslag import DataSet

# TODO fill
ENERGY_TYPES = ["Electricity", "Coal", "Natural Gas"]
FEEDSTOCK_TYPES = ["Oxygen", "Iron Ore", "Scrap Steel"]
EMISSION_TYPES = ["CO2"]
ALLOWED_TYPES = {
    "High CAPEX",
    "Low CAPEX",
    "Energy demand",
    "Feedstock demand",
    "OPEX",
    "Emissions"
}
EXPECTED_REMOVAL_TYPES = {
        # specified in project description
        "Lifetime",
        "OCF",
        "Output Capacity",
        "Output",
    }
POSTED_OPEX_COMPONENTS = ['OPEX Variable', 'OPEX Fixed']
ALLOWED_COMPONENTS = {
    "CAPEX",
    "Additional OPEX",
}
TRANSLATION = {"Fossil Gas": "Natural Gas"}


# TODO add low capex
# TODO get emissions via emissions factor
# TODO sort by Technology

def generate_cacoca_input(posted_datafolder: Path, target_folder: Path):
    technames = find_posted_technames(posted_datafolder)
    for techname in technames:
        print(f"Processing Posted technology file: {techname}")
        df_posted, posted_parent_variable = get_posted_df(techname)
        df_cacoca = translate_posted_df_to_cacoca_df(df_posted, posted_parent_variable)
        save_cacoca_dataframe(df_cacoca, target_folder, techname)

def find_posted_technames(posted_datafolder: Path):
    """Find available Posted technology files in the given folder."""
    return [f.stem for f in posted_datafolder.glob("*.csv")]

def get_posted_df(posted_techname):
    posted_parent_variable = f"Tech|{posted_techname}"
    teds = DataSet(posted_parent_variable)
    df_posted = teds.aggregate(region="World", period=2025) 
    df_posted.drop(columns=["region"], inplace=True) # region is redundant
    return df_posted, posted_parent_variable

def translate_posted_df_to_cacoca_df(df_posted: pd.DataFrame, posted_parent_variable: str) -> pd.DataFrame:
    df_cacoca = initiate_cacoca_dataframe(df_posted, posted_parent_variable)
    df_cacoca = aggregate_opex(df_cacoca)
    df_cacoca = filter_cacoca_dataframe(df_cacoca)
    return df_cacoca

def initiate_cacoca_dataframe(df_posted: pd.DataFrame, posted_parent_variable: str) -> pd.DataFrame:
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

    return df_cacoca

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

    elif type_ in POSTED_OPEX_COMPONENTS:
        component = type_ # variable and fixed opex will later be combined to additional opex
        type_ = "OPEX"
    
    elif type_ ==  "Input":
        if component in ENERGY_TYPES:
            type_ = "Energy demand"
        elif component in FEEDSTOCK_TYPES:
            type_ = "Feedstock demand"
        else:
            raise ValueError(f"Unknown component {component} for Input variable")

    component = TRANSLATION.get(component, component)
    
    return {"Type": type_, "Component": component}
            
def aggregate_opex(df_cacoca: pd.DataFrame) -> pd.DataFrame:
    # TODO Warning: This assumes OPEX and CAPEX have compatible unit!
    is_opex_mask = df_cacoca['Component'].isin(POSTED_OPEX_COMPONENTS)
    df_opex = df_cacoca[is_opex_mask].copy()
    df_other = df_cacoca[~is_opex_mask]

    if not df_opex.empty:
        # sort (as OPEX Variable should be the master for other columns): 
        df_opex['Component'] = pd.Categorical(df_opex['Component'], categories=POSTED_OPEX_COMPONENTS, ordered=True)
        df_opex = df_opex.sort_values("Component")

        # aggregate OPEX components
        grouping_cols = [col for col in df_cacoca.columns if col not in ['Component', 'Value', 'Unit']]
        agg_logic = {'Value': 'sum', 'Unit': 'first'}
        aggregated_opex = df_opex.groupby(grouping_cols, as_index=False, dropna=False).agg(agg_logic)
        aggregated_opex['Component'] = 'Additional OPEX'

        # add aggregated OPEX back to CaCoCa dataframe
        df_cacoca = pd.concat([df_other, aggregated_opex], ignore_index=True)
    
    return df_cacoca

def filter_cacoca_dataframe(df_cacoca: pd.DataFrame) -> pd.DataFrame:
    ALLOWED_COMPONENTS.update(ENERGY_TYPES, FEEDSTOCK_TYPES, EMISSION_TYPES)

    # Find rows in df_translated with new types/components
    mask_type = df_cacoca["Type"].isin(ALLOWED_TYPES)
    mask_component = df_cacoca["Component"].isin(ALLOWED_COMPONENTS)
    mask_valid = mask_type & mask_component

    # Warn about dropped rows
    dropped_rows = df_cacoca[~mask_valid]
    unexpected_dropped = dropped_rows[~dropped_rows["Type"].isin(EXPECTED_REMOVAL_TYPES)]
    if not unexpected_dropped.empty:
        unique_dropped = unexpected_dropped[["Type", "Component"]].drop_duplicates()
        print("Warning: Unexpected unique Type/Component combinations are dropped:")
        print(unique_dropped)

    # Keep only valid rows
    df_cacoca = df_cacoca[mask_valid]

    return df_cacoca

def save_cacoca_dataframe(df_cacoca: pd.DataFrame, target_folder: Path, posted_filename: str):
    # ensure target folder exists
    target_folder.mkdir(parents=True, exist_ok=True)

    df_cacoca_path = target_folder / f"{posted_filename}.csv"
    df_cacoca.to_csv(df_cacoca_path, index=False)
