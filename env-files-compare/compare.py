from config import EnvFilesCompareConfig
from loader import EnvFileLoader


class EnvFilesCompare:
  def __init__(self, config: EnvFilesCompareConfig):
    self.config = config
    self.differences = {}

  def compare(self):
    env_vars = []
    self.differences = {}
    all_keys = set()
    
    for path in self.config.paths:
      env_vars.append(EnvFileLoader.load_env_file(path))
      all_keys = all_keys.union(set(env_vars[-1].keys()))

    for key in all_keys:
      values = []
      # Get the value for the key from each env file, if it exists
      for env_var in env_vars:
        values.append(env_var.get(key))
      # Check if any of the values are None (key missing in one of the files)
      if any(v is None for v in values):
        self.differences[key] = tuple(values)
      # Check if the values are different across the files
      elif len(set(values)) > 1:
        self.differences[key] = tuple(values)
    return self.differences

  def report(self):
    if not self.differences: 
      print("No differences found between the two environment files.")
    else:
      print("Differences found:")
      for key, values in self.differences.items():
        print(f"  {key}:")
        for i, value in enumerate(values):
          print(f"    Path {i + 1}: {value}")
