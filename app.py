# MOPTAX RDN Delivery - Streamlit App
import streamlit as st
import pandas as pd
import geopandas as gpd
from io import BytesIO

# ------------------------ Function Definitions ------------------------

def load_files(devzones, lat_lon, company_internal, company_remove):
    """Load uploaded files into dataframes and return them."""
    sf_zones = gpd.read_file(devzones).rename(columns={"Delivery.Zone": "Distr_code"}).to_crs(4326)
    lat_lon_data = pd.read_csv(lat_lon)
    company_internal_data = pd.read_csv(company_internal)
    company_remove_data = pd.read_csv(company_remove)
    return sf_zones, lat_lon_data, company_internal_data, company_remove_data

def process_data(sf_zones, lat_lon_data, company_remove_data):
    """Process property data by performing spatial joins and filtering."""
    # Convert properties to GeoDataFrame
    sf_prop = gpd.GeoDataFrame(
        lat_lon_data.dropna(subset=["coordinate_lat"]),
        geometry=gpd.points_from_xy(lat_lon_data.coordinate_lng, lat_lon_data.coordinate_lat),
        crs="EPSG:4326"
    )

    # Spatial join: Assign properties to delivery zones
    sf_prop_assigned = gpd.sjoin(sf_prop, sf_zones, how="left", op="within")

    # Filter out properties that should be removed
    properties_to_remove = company_remove_data["property_code_assigned"].unique()
    sf_prop_assigned = sf_prop_assigned[
        ~sf_prop_assigned["property_code_assigned"].isin(properties_to_remove)
    ]

    # Return processed data (without geometry for export)
    return sf_prop_assigned.drop(columns="geometry")

def create_download_button(dataframe, filename, label):
    """Create a download button for the processed data."""
    buffer = BytesIO()
    dataframe.to_csv(buffer, index=False)
    buffer.seek(0)
    st.download_button(
        label=label,
        data=buffer,
        file_name=filename,
        mime="text/csv"
    )

# ------------------------ Streamlit UI Layout ------------------------

# Set app title
st.title("MOPTAX RDN Delivery")

# File upload section
st.subheader("Step 1: Upload Required Files")
devzones_gpkg = st.file_uploader("Upload Delivery Zones (GeoPackage)", type=["gpkg"])
lat_lon_csv = st.file_uploader("Upload Latitude/Longitude Data (CSV)", type=["csv"])
company_internal_csv = st.file_uploader("Upload Internal Delivery Properties (CSV)", type=["csv"])
company_remove_csv = st.file_uploader("Upload Properties to Remove (CSV)", type=["csv"])

# Process button (visible only if all files are uploaded)
if all([devzones_gpkg, lat_lon_csv, company_internal_csv, company_remove_csv]):
    if st.button("Process Data"):
        # Load files into dataframes
        sf_zones, lat_lon_data, company_internal_data, company_remove_data = load_files(
            devzones_gpkg, lat_lon_csv, company_internal_csv, company_remove_csv
        )

        # Process the data
        st.write("Processing data... Please wait.")
        processed_data = process_data(sf_zones, lat_lon_data, company_remove_data)

        # Display results
        st.success("Processing completed! Download your files below.")
        st.write("### Processed Properties")
        st.dataframe(processed_data.head())

        # Provide download button for the processed data
        create_download_button(processed_data, "processed_properties.csv", "Download Processed Properties")
else:
    st.warning("Please upload all required files to enable processing.")
