
import json
from os import read

json_file_path = 'fuisql-dictionary.json'  # Path to your JSON file

# Method 2: Counting parent elements from a JSON file
# Assuming you have a file named 'data.json' in the same directory
try:
    with open(json_file_path, 'r') as f:
        data_from_file = json.load(f)
    file_count = len(data_from_file)
    print(f"The number of parent elements in the file is: {file_count}")
except FileNotFoundError:
    print(f"{json_file_path} not found. Please create the file or adjust the path.")
