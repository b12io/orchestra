
def convert_key_to_int(d):
    return {int(k) if k.lstrip('-').isdigit() else k: v for k, v in d.items()}
