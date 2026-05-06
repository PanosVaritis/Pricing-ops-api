import azure_data
import google_data
import aws_data

def main():
    try:
        print("Running script to injest data from providers\n")
        azure_data.main()
        print()
        aws_data.main()
        print()
        google_data.main()
        print()

    except Exception as e:
        print ("Error ")


if __name__ == "__main__":
    main()