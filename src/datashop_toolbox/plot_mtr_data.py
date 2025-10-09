import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import LassoSelector
from matplotlib.path import Path
import matplotlib.dates as mdates

from datashop_toolbox.odfhdr import OdfHeader

# Load ODF data
odf = OdfHeader()
odf.read_odf('C:/DFO-MPO/DEV/MTR/999_Test/MTR_BCD2014999_002_1273003_600.ODF')
orig_df = odf.data.data_frame

# Extract temperature and time
temp = orig_df['TE90_01'].to_numpy()
sytm = orig_df['SYTM_01'].str.lower().str.strip("'")
dt = pd.to_datetime(sytm, format='%d-%b-%Y %H:%M:%S.%f')

# Create a DataFrame with Temperature as the variable and DateTime as the index.
df = pd.DataFrame({'Temperature': temp}, index=dt)

# Convert datetime to numeric for lasso selection
xy = np.column_stack([mdates.date2num(df.index), df['Temperature']])

# List to store selected points
selected_points = []

# Plot
fig, ax = plt.subplots(figsize=(10, 6))
pts = ax.scatter(df.index, df['Temperature'], s=10, color='blue')
plt.title('Time Series Data')
plt.xlabel('Date Time')
plt.ylabel('Temperature')
plt.grid(True)

# Lasso callback
def onselect(verts):
    path = Path(verts)
    ind = np.nonzero(path.contains_points(xy))[0]
    selected = xy[ind]
    ax.scatter(mdates.num2date(selected[:, 0]), selected[:, 1], color='red', s=20)
    plt.draw()

    # Store selected points
    selected_dt = mdates.num2date(selected[:, 0])
    selected_temp = selected[:, 1]
    selected_df = pd.DataFrame({'DateTime': selected_dt, 'Temperature': selected_temp})
    selected_points.append(selected_df)
    print("Selected points:")
    print(selected_df)

# Activate lasso
lasso = LassoSelector(ax, onselect)

plt.show()

# After closing the plot, you can access all selected points
if selected_points:
    all_selected_df = pd.concat(selected_points, ignore_index=True)
    print("All captured points:")
    print(all_selected_df)
