import re

image_file_regex = re.compile('([-\w]+\.(?:jpg|jpeg|gif|png|svg))',
                              re.IGNORECASE)
