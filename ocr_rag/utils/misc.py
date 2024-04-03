import yaml

def get_cfg(cfg_path: str):
    with open(cfg_path) as f:
        cfg = yaml.safe_load(f)
    return cfg