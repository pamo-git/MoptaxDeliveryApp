# MOPTAX RDN Delivery - Streamlit App with Google Drive Integration
import streamlit as st
import pandas as pd
import geopandas as gpd
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import os

# ------------------------ Google Drive Authentication ------------------------

def authenticate_drive():
    """Authenticate Google Drive using service account credentials."""
    gauth = GoogleAuth()
    gauth.LoadCredentialsFile("service_account.json")  # Upload your service account JSON
    if gauth.credentials is None:
        st.error("Service account authentication failed.")
        return None
    return GoogleDrive(gauth)

# ------------------------ File Manipulation on Google Drive ------------------------

def list_drive_files(drive, folder_id):
    """List all PDF files in the given Google Drive folder."""
    file_list = drive.ListFile({'q': f"'{folder_id}' in parents and mimeType='application/pdf'"}).GetList()
    return {f['title']: f['id'] for f in file_list}

def create_drive_folder(drive, parent_id, folder_name):
    """Create a new folder on Google Drive."""
    folder = drive.CreateFile({
        'title': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [{'id': parent_id}]
    })
    folder.Upload()
    return folder['id']

def move_file_to_folder(drive, file_id, new_folder_id):
    """Move a file to the specified folder on Google Drive."""
    file = drive.CreateFile({'id': file_id})
    file['parents'] = [{'id': new_folder_id}]
    file.Upload()

# ------------------------ Data Processing ------------------------

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

# ------------------------ Streamlit UI Layout ------------------------

# Set page configuration
st.set_page_config(page_title="MOPTAX RDN Delivery", page_icon="📦", layout="wide")

# Header section with a modern title
st.markdown(
    """
    <style>
    .title {
        font-size: 42px;
        font-weight: bold;
        text-align: center;
        color: #FF4B4B;
    }
    </style>
    <div class="title">📦 MOPTAX RDN Delivery System</div>
    """, 
    unsafe_allow_html=True
)
st.write("A modern solution for organizing and managing RDN files for efficient delivery.")

# Sidebar for uploads and inputs
with st.sidebar:
    st.header("Upload Required Files")
    devzones_gpkg = st.file_uploader("📍 Delivery Zones (GeoPackage)", type=["gpkg"])
    lat_lon_csv = st.file_uploader("📋 Latitude/Longitude Data (CSV)", type=["csv"])
    company_internal_csv = st.file_uploader("🏢 Internal Delivery Properties (CSV)", type=["csv"])
    company_remove_csv = st.file_uploader("🚫 Properties to Remove (CSV)", type=["csv"])

    st.header("Google Drive Folder ID")
    folder_id = st.text_input("🔗 Enter Google Drive Folder ID")

    st.info("Ensure that the folder is shared with the service account.")

# Process button centered in the main layout
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🚀 Process Data"):
        if all([devzones_gpkg, lat_lon_csv, company_internal_csv, company_remove_csv, folder_id]):
            # Authenticate with Google Drive
            with st.spinner("Authenticating with Google Drive..."):
                drive = authenticate_drive()
                if not drive:
                    st.stop()

            # Load uploaded files into dataframes
            sf_zones = gpd.read_file(devzones_gpkg).rename(columns={"Delivery.Zone": "Distr_code"}).to_crs(4326)
            lat_lon_data = pd.read_csv(lat_lon_csv)
            company_remove_data = pd.read_csv(company_remove_csv)

            # Process the data
            st.write("🔄 Processing data... Please wait.")
            processed_data = process_data(sf_zones, lat_lon_data, company_remove_data)

            # List RDN files in the Google Drive folder
            st.write("📂 Organizing RDN files on Google Drive...")
            rdn_files = list_drive_files(drive, folder_id)

            # Create grouped folders and move files
            for _, row in processed_data.iterrows():
                zone_folder_id = create_drive_folder(drive, folder_id, row["Distr_code"])
                rdn_filename = f"{row['property_code_assigned']}.pdf"

                if rdn_filename in rdn_files:
                    move_file_to_folder(drive, rdn_files[rdn_filename], zone_folder_id)

            st.success("🎉 Processing completed! Your RDN files are organized.")
            st.write(f"👉 [Access your organized folder on Google Drive](https://drive.google.com/drive/folders/{folder_id})")
        else:
            st.warning("⚠️ Please upload all required files and provide the Google Drive folder ID.")

# Footer with a subtle copyright message
st.markdown(
    """
    <hr style="border:1px solid #FF4B4B;">
    <p style="text-align: center;">Copyright © 2024 MOPTAX RDN Delivery. All rights reserved.</p>
    """, 
    unsafe_allow_html=True
)
