import re

image_file_regex = re.compile('([-\w\s]+\.(?:jpg|jpeg|gif|png|svg))',
                              re.IGNORECASE)
