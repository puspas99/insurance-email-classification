import json


def read_file(file_path):
    try:
        with open(file_path, 'r') as file:
            content = file.read()
        return content
    except FileNotFoundError:
        print(f"Error: The file at {file_path} was not found.")
        return None
    except IOError as e:
        print(f"Error: Unable to read the file. {e}")
        return None


import os


def read_most_recent_file(directory):

    try:
        # List all files in the directory
        files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]

        if not files:
            print("No files found in the directory.")
            return None

        # Get the full path of the most recently modified file
        most_recent_file = max(files, key=lambda f: os.path.getmtime(os.path.join(directory, f)))

        # Read and return the content of the most recently modified file
        most_recent_file_path = os.path.join(directory, most_recent_file)
        with open(most_recent_file_path, 'r') as file:
            content = file.read()

        return content

    except Exception as e:
        print(f"Error: {e}")
        return None


def delete_all_files_in_folder(directory):

    try:
        if not os.path.exists(directory):
            return

        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                import shutil
                print("Silently deleting the files :"+file_path)
                shutil.rmtree(file_path)
    except Exception as e:
        pass

def read_all_files_in_directory(directory):

    try:
        # List all files in the directory
        files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]

        if not files:
            print("No files found in the directory.")
            return {}

        # Dictionary to store file names and their contents
        file_contents = {}

        for file_name in files:
            file_path = os.path.join(directory, file_name)
            try:
                with open(file_path, 'r') as file:
                    content = file.read()
                file_contents[file_name] = content
            except Exception as file_error:
                print(f"Could not read {file_name}: {file_error}")

        # Convert the dictionary to a JSON object
        return json.dumps(file_contents, indent=4)

    except Exception as e:
        print(f"Error: {e}")
        return None