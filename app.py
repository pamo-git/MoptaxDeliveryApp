# MOPTAX RDN Delivery - Streamlit App
import streamlit as st
import pandas as pd
import geopandas as gpd
import os
import shutil
from io import BytesIO
from zipfile import ZipFile

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
    sf_prop = gpd.GeoDataFrame(
        lat_lon_data.dropna(subset=["coordinate_lat"]),
        geometry=gpd.points_from_xy(lat_lon_data.coordinate_lng, lat_lon_data.coordinate_lat),
        crs="EPSG:4326"
    )

    sf_prop_assigned = gpd.sjoin(sf_prop, sf_zones, how="left", op="within")

    properties_to_remove = company_remove_data["property_code_assigned"].unique()
    sf_prop_assigned = sf_prop_assigned[
        ~sf_prop_assigned["property_code_assigned"].isin(properties_to_remove)
    ]

    return sf_prop_assigned.drop(columns="geometry")

def download_google_drive_folder(link, download_dir="rdn_files"):
    """Download files from a Google Drive folder link (requires gdown)."""
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    
    # This command assumes you have `gdown` installed and available.
    # Replace with the appropriate Google Drive API solution if needed.
    os.system(f"gdown --folder {link} -O {download_dir}")
    return download_dir

def sort_files_into_folders(processed_data, download_dir):
    """Sort and group files into folders based on processed data."""
    grouped_dir = "grouped_files"
    os.makedirs(grouped_dir, exist_ok=True)

    for _, row in processed_data.iterrows():
        # Create folder path based on delivery zone
        folder_path = os.path.join(grouped_dir, row["Distr_code"])
        os.makedirs(folder_path, exist_ok=True)

        # Find the corresponding RDN file in the download directory
        rdn_filename = f"{row['property_code_assigned']}.pdf"  # Assumes RDNs are named with property code
        src_file = os.path.join(download_dir, rdn_filename)

        if os.path.exists(src_file):
            shutil.copy(src_file, folder_path)

    return grouped_dir

def zip_grouped_folders(grouped_dir):
    """Zip the grouped folders for download."""
    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, "w") as zf:
        for root, _, files in os.walk(grouped_dir):
            for file in files:
                zf.write(os.path.join(root, file), arcname=os.path.relpath(os.path.join(root, file), grouped_dir))
    zip_buffer.seek(0)
    return zip_buffer

# ------------------------ Streamlit UI Layout ------------------------

st.title("MOPTAX RDN Delivery")

st.subheader("Step 1: Upload Required Files")
devzones_gpkg = st.file_uploader("Upload Delivery Zones (GeoPackage)", type=["gpkg"])
lat_lon_csv = st.file_uploader("Upload Latitude/Longitude Data (CSV)", type=["csv"])
company_internal_csv = st.file_uploader("Upload Internal Delivery Properties (CSV)", type=["csv"])
company_remove_csv = st.file_uploader("Upload Properties to Remove (CSV)", type=["csv"])

st.subheader("Step 2: Provide Google Drive Folder Link")
google_drive_link = st.text_input("Paste Google Drive folder link containing RDN files:")

if st.button("Process Data"):
    if all([devzones_gpkg, lat_lon_csv, company_internal_csv, company_remove_csv, google_drive_link]):
        # Load the uploaded files
        sf_zones, lat_lon_data, company_internal_data, company_remove_data = load_files(
            devzones_gpkg, lat_lon_csv, company_internal_csv, company_remove_csv
        )

        # Download RDN files from Google Drive
        st.write("Downloading RDN files from Google Drive...")
        download_dir = download_google_drive_folder(google_drive_link)

        # Process the data
        st.write("Processing data... Please wait.")
        processed_data = process_data(sf_zones, lat_lon_data, company_remove_data)

        # Sort files into grouped folders
        st.write("Sorting files into group folders...")
        grouped_dir = sort_files_into_folders(processed_data, download_dir)

        # Zip the grouped folders for download
        zip_buffer = zip_grouped_folders(grouped_dir)

        # Provide a download button for the zipped grouped folders
        st.success("Processing completed! Download your grouped files below.")
        st.download_button(
            label="Download Grouped Files (ZIP)",
            data=zip_buffer,
            file_name="grouped_files.zip",
            mime="application/zip"
        )
    else:
        st.warning("Please upload all required files and provide the Google Drive link.")
