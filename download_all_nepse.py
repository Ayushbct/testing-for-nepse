import requests

def download_file(url, filename=None):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raise an error for bad status codes

        if not filename:
            filename = url.split("/")[-1]  # Default to the last part of the URL

        with open(filename, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"Downloaded: {filename}")
    except requests.exceptions.RequestException as e:
        print(f"Download failed: {e}")

# Example usage
if __name__ == "__main__":
    url = "https://omitnomis.github.io/ShareSansarScraper/Data/combined_excel.xlsx"  # Replace with your URL
    download_file(url)
