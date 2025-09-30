import streamlit as st
import pandas as pd
import json
import re

# --- Set up the page configuration ---
st.set_page_config(
    page_title="Interactive Data Dashboard",
    page_icon="📊",
    layout="wide"
)

# --- Define a function to intelligently load nested JSON data ---
def load_nested_json(file_content):
    """
    Loads JSON data. If the top level is a dict, it attempts to find 
    the list of records to convert to a DataFrame.
    """
    try:
        data = json.load(file_content)
    except json.JSONDecodeError:
        # File is likely empty or malformed
        return None, "Error: Could not decode JSON. File may be malformed or empty."

    # Case 1: Data is already a list (standard JSON array of objects)
    if isinstance(data, list):
        return pd.DataFrame(data), None

    # Case 2: Data is a dict (nested structure)
    elif isinstance(data, dict):
        st.info("Uploaded JSON is a dictionary. Searching for a nested list of records...")
        
        # Heuristic: Find the first value that is a non-empty list
        for key, value in data.items():
            if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                st.success(f"Successfully extracted list of records from key: **{key}**")
                return pd.DataFrame(value), None

        # Fallback: Try to normalize the entire dictionary
        try:
            # This is a last resort and may fail for complex nesting
            return pd.json_normalize(data), None
        except Exception:
             return None, "Error: Could not find a suitable list of records inside the dictionary."
    
    else:
        # E.g., a simple string or integer at the root
        return None, "Error: JSON root element is not a list or dictionary."

# --- Define a function to detect and configure URL columns ---
def detect_url_columns(df: pd.DataFrame) -> dict:
    """
    Analyzes a DataFrame to identify columns containing URLs.
    Returns a dictionary suitable for st.dataframe's column_config.
    """
    url_cols_config = {}
    for col in df.columns:
        # Heuristic: Check if the column is of 'object' (string) type
        # and if the first 10 non-empty values look like a URL.
        sample_values = df[col].dropna().head(10)
        if df[col].dtype == 'object' and any(isinstance(val, str) and re.match(r'https?://', val) for val in sample_values):
            url_cols_config[col] = st.column_config.LinkColumn(
                f"{col} (Link)",
                help=f"Click to open the link in {col}",
                display_text="🔗 View Link"
            )
    return url_cols_config

# --- Left Sidebar for Description and Instructions ---
with st.sidebar:
    st.title("Dashboard Instructions 📋")
    st.info(
        """
        Welcome to the Interactive Data Dashboard!

        1.  **Upload your File:** Use the file uploader to select a **.json** or **.csv** file.
            * **JSON Handling:** If your JSON is a dictionary with a nested list of records (a common format), the app will **automatically extract that list** to ensure proper viewing.
        2.  **Choose Display Mode:** Decide if you want to see all columns or select specific ones.
        3.  **Set Rows per Page:** Enter the number of rows you wish to view on a single page.
        4.  **Navigate:** Use the "Next" and "Previous" buttons to browse through your data.
        """
    )
    st.markdown("---")
    st.subheader("Built with ❤️")
    st.write("A professional tool for quick data exploration.")

# --- Main Dashboard Content ---
st.title("Dynamic Data Explorer 📈")
st.markdown("Upload your data and interact with it below.")
st.markdown("---")

# --- File Uploader ---
uploaded_file = st.file_uploader("Choose a CSV or JSON file to upload", type=["csv", "json"])

if uploaded_file is not None:
    # Use uploaded_file.seek(0) to ensure reading from the start of the file
    uploaded_file.seek(0) 

    try:
        df = None
        error_message = None
        
        # Read the file based on its type
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith('.json'):
            # Use the specialized JSON loading function
            df, error_message = load_nested_json(uploaded_file)
        
        if error_message:
            st.error(error_message)
            st.stop()
            
        if df is None or df.empty:
            st.warning("The file was processed, but the resulting DataFrame is empty.")
            st.stop()

        # Initialize session state variables
        if 'df_original' not in st.session_state or st.session_state.df_original.equals(df) is False:
            st.session_state.df_original = df
            st.session_state.page = 0
            
        # --- Column Selection UI ---
        st.subheader("Data Display Settings")
        col_option = st.radio(
            "Which columns would you like to view?",
            ("All Columns", "Selected Columns"),
            index=0
        )
        
        # Apply column filtering based on user choice
        if col_option == "Selected Columns":
            all_cols = list(st.session_state.df_original.columns)
            selected_cols = st.multiselect(
                "Select the columns to display:",
                all_cols,
                default=all_cols
            )
            if not selected_cols:
                st.warning("Please select at least one column to display.")
                st.stop()
            display_df = st.session_state.df_original[selected_cols]
        else:
            display_df = st.session_state.df_original
        
        # --- Pagination UI ---
        st.subheader("Pagination Controls")
        rows_per_page = st.number_input(
            "Number of rows per page:",
            min_value=1,
            value=10,
            step=1
        )
        
        total_rows = len(display_df)
        total_pages = (total_rows - 1) // rows_per_page + 1

        # --- Display Data and Navigation ---
        st.subheader(f"Displaying Data (Page {st.session_state.page + 1} of {total_pages})")
        
        start_row = st.session_state.page * rows_per_page
        end_row = start_row + rows_per_page
        
        paged_df = display_df.iloc[start_row:end_row]
        
        # Automatically detect URL columns and configure them for clickable links
        url_config = detect_url_columns(paged_df)
        
        st.dataframe(
            paged_df,
            column_config=url_config,
            use_container_width=True,
            hide_index=True
        )
        
        # --- Navigation Buttons ---
        col1, col2, col3 = st.columns([1, 1, 8])
        
        with col1:
            if st.button("Previous"):
                if st.session_state.page > 0:
                    st.session_state.page -= 1
                    st.rerun()
                else:
                    st.warning("You are on the first page.")
        
        with col2:
            if st.button("Next"):
                if st.session_state.page < total_pages - 1:
                    st.session_state.page += 1
                    st.rerun()
                else:
                    st.warning("You are on the last page.")

    except Exception as e:
        st.error(f"An unexpected error occurred while processing the file: {e}")
        st.info("Please ensure your file is correctly formatted.")
else:
    st.info("👆 Please upload a file to begin.")
