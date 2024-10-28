def strtobool(val):
    val = val.lower()
    if val in {'y', 'yes', 't', 'true', 'on', '1'}:
        return True
    elif val in {'f', 'false', 'no', 'n', '0'}:
        return False
    else:
        return ValueError(f'Invalid truth value {val}')