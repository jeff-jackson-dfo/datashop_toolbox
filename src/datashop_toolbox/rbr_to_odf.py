from pyrsktools import RSK
from icecream import ic
import matplotlib.pyplot as plt



def convert_rbr_to_odf(rsk_file_path: str, station_latitude: float = 0.0, station_longitude: float = 0.0):

    # Open the RSK file. Metadata is read here
    with RSK(rsk_file_path) as rsk:

        # Read, process, view, or export data here
        # ic(rsk.filename)
        # ic(rsk.version)
        # print(rsk)

        # Read the data into a numpy ndarray
        rsk.readdata()
        # ic(len(rsk.data))
        # ic(rsk.data["depth"])

        # 1. Shift temperature channel of the first four profiles with the same lag value.
        # rsk.alignchannel(channel="temperature", lag=2, profiles=range(0,3))

        # 2. Shift oxygen channel of first 4 profiles with profile-specific lags.
        # rsk.alignchannel(channel="dissolved_o2_concentration", lag=[2,1,-1,0], profiles=range(0,3))

        # 3. Shift conductivity channel from all downcasts with optimal lag calculated with calculateCTlag().
        # lag = rsk.calculateCTlag()
        # print(lag)
        # rsk.alignchannel(channel="conductivity", lag=lag)
        
        # Apply a thermal mass correction to conductivity using the model of Lueck and Picklo (1990).
        # rsk.correctTM(alpha=0.04, beta=0.1)

        rsk.derivesigma(latitude=station_latitude, longitude=station_longitude)
        # rsk.derivevelocity()
        
        # rsk.correcttau(channel="dissolved_o2_concentration", tauResponse=0)

        # Print channel names after adding new channels
        # print(rsk.channelNames)
        for channel in rsk.channels:
            ic(channel.longName)
            ic(channel._dbName)
            ic(channel.units)

        # Display in succession a plot of each profile in the dataset
        # profiles = rsk.getprofilesindices(range(0, 3), direction="both")
        profiles = rsk.getprofilesindices(range(0, 3), direction="both")
        for p, profileIndices in enumerate(profiles):
            if p == 1:
                # print(f"Plotting profile {p}")
                # rsk.removeloops(profiles=[p,p])
                # print(rsk.data[profileIndices])
                fig, axes = rsk.plotprofiles(
                    channels=["temperature", "conductivity", "salinity", "density_anomaly", "dissolved_o2_concentration"],
                    profiles=(p,p),
                    direction="down",
                )
                plt.show()

        print(rsk.logs)

def main():
    rsk_file_path = "C:/DFO-MPO/DEV/Data/2025/BCD2025669/DATASHOP_PROCESSING/RBR/237747_20251121_1144.rsk"
    lat = 44.932883
    long = -66.842617
    convert_rbr_to_odf(rsk_file_path, lat, long)

if __name__ == "__main__":
    main()
