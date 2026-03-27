def open_file(file_name):
    with open(file_name, 'r') as file:
        content = file.read()
    return content

def write_file(file_name, content):
    with open(file_name, 'w') as file:
        file.write(content)


def get_file_list():
    import os
    files = []
    for dirpath, dirnames, filenames in os.walk('.'):
        for filename in filenames:
            files.append(os.path.join(dirpath, filename))
    return files