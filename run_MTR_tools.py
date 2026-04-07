from datashop_toolbox.ai_thermograph_data import main as ai_thermograph_data
from datashop_toolbox.process_mtr_files import main as process_mtr_files
from datashop_toolbox.qc_thermograph_data_old import main as qc_thermograph_data


def main():
    print("\nSelect the tool you want to run:\n")
    print("1 ➜ Process raw MTR files")
    print("2 ➜ QC thermograph data")
    print("3 ➜ AI thermograph data (under development)\n")

    choice = input("Enter your choice (1 or 2 or 3): ").strip()

    if choice == "1":
        print("\n▶ Running Process MTR Files...\n")
        process_mtr_files()

    elif choice == "2":
        print("\n▶ Running QC Thermograph Data...\n")
        qc_thermograph_data()
    
    elif choice == "3":
        print("\n▶ Running AI on Thermograph Data...\n")
        ai_thermograph_data()

    else:
        print("\n❌ Invalid choice. Please enter 1 or 2 or 3.\n")


if __name__ == "__main__":
    main()