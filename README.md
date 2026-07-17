# datashop_toolbox
**Unclassified – Non Classifié**

---

## 🌊 Overview
The **datashop_toolbox** is a Python-based data processing and quality control (QC) toolbox developed by the **Ocean Data Information Section (ODIS)** at the **Bedford Institute of Oceanography (BIO)**, Fisheries and Oceans Canada (DFO).

This toolbox supports the processing, QC, and archival preparation of oceanographic data, including:

- CTD data (from Sea-Bird and RBR Global instruments)
- Moored temperature (thermograph) data

### 🎯 Objective
The primary goal is to convert raw and semi-processed instrument data into **DFO’s Ocean Data Format (ODF)** while enforcing **robust and reproducible QC workflows**.

---

## 👨‍🔬 Authors
- **Jeff Jackson**, Fisheries and Oceans Canada (DFO)  
- **Prodyut Kumar Roy**, Fisheries and Oceans Canada (DFO)  

Developed and maintained by **ODIS** at the Bedford Institute of Oceanography (BIO).

---

## ⚙️ Installation

### 1️⃣ Requirements
- Python ≥ 3.11  
- numpy  
- pandas
- matplotlib  
- pyside6 (for GUI QC tools)
- scipy
- netCDF4
- gsw

---

### 2️⃣ Setup

#### Step 1: Download the Package
There are two ways to handle this step.
##### a. Clone the Git Repo by running command in terminal window
Git must be installed first (https://git-scm.com/install/windows)
> git clone https://github.com/jeff-jackson-dfo/datashop_toolbox.git
##### b. Download the Git Repo as a ZIP file and unzip it
https://github.com/jeff-jackson-dfo/datashop_toolbox/archive/refs/heads/master.zip

After package is on your system, open a Terminal window and change the working
directory to be the folder where the package is located (cloned or unzipped).

*The following commands will be run in the open terminal window.*

#### Step 2: Create environment
#### Install uv if required
(On Windows) 
https://docs.astral.sh/uv/getting-started/installation/

> uv venv

#### Step 3: Activate environment
> .venv\Scripts\activate

#### Step 4: Install dependencies
> uv sync

#### Step 5: Build Wheel File
> uv build --wheel

#### Step 6: Add package
> uv add <path_to_whl>\datashop_toolbox-<version>-py3-none-any.whl

e.g. uv add dist\datashop_toolbox-1.1.0.5-py3-none-any.whl

**Now you can import all or parts of the Datashop Python Toolbox to use in a script or run in a terminal window.**

▶️ Run Toolbox 

- To process and QC MTR (Moored Temp Record) data
   ## Run MTR tools

   uv run run_MTR_tools.py

   or

   uv run python -m run_MTR_tools

## 📁 Package Structure

```text
datashop_toolbox/
├── src/
│   ├── datashop_toolbox/
│   │   ├── headers/                     # ODF header classes
│   │   ├── thermograph.py               # Thermograph processing core
│   │   ├── qc_thermograph_data.py       # QC for thermograph data
│   │   └── process_mtr_files.py         # MTR processing pipeline
│   │
│   ├── seabird/
│   │   ├── cnv.py                       # Sea-Bird CNV parser
│   │   └── cnv.json                     # CNV parsing rules
│   │
│   ├── CoTeDe/
│   │   └── qc.py                        # Custom QC tests
│
├── ▶️ run_SEABIRD_tools.py                 # Example Sea-Bird runner to Load DFO standard .CNV files
├── ▶️ run_MTR_tools.py                     # Example MTR runner to process MTR Data
├── README.md
└── ODF_File_Specification.md
``



## 🧩 Core Components

### 1️⃣ `datashop_toolbox` (DFO Proprietary)

Implements core processing using Python OOP principles:

- Reading raw MTR and CTD data  
- Structured metadata handling  
- Quality flag assignment  
- Writing to **Ocean Data Format (ODF)**  

📄 **ODF Specification (v3.0):**  
👉 https://github.com/jeff-jackson-dfo/datashop_toolbox/blob/master/ODF_File_Specification.md  

---

### 2️⃣ Sea-Bird CNV Parsing (`seabird`)

Extends the PySeabird parser for CNV files.

#### ✨ Features
- Supports multiple Sea-Bird firmware formats  
- Handles:
  - Commented XML / CDATA blocks  
  - Partial metadata (lat/lon, station, cast)  
- Stores data as NumPy masked arrays  
- Converts DMS → decimal degrees automatically  

#### 💡 Example
```python
from seabird.cnv import fCNV

profile = fCNV("input_file.CNV")

# Defensive defaults (recommended)
profile.attrs.setdefault("LATITUDE", "")
profile.attrs.setdefault("LONGITUDE", "")

df = profile.as_DataFrame()
