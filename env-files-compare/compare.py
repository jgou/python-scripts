from config import EnvFilesCompareConfig
from loader import EnvFileLoader


class EnvFilesCompare:
  def __init__(self, config: EnvFilesCompareConfig):
    self.config = config
    self.differences = {}

  def compare(self):
    env_vars1 = EnvFileLoader.load_env_file(self.config.path1)
    env_vars2 = EnvFileLoader.load_env_file(self.config.path2)
    self.differences = {}
    all_keys = set(env_vars1.keys()).union(set(env_vars2.keys()))
    for key in all_keys:
      if key not in env_vars1:
        self.differences[key] = (None, env_vars2[key])
      elif key not in env_vars2:
        self.differences[key] = (env_vars1[key], None)
      else:
        if env_vars1[key] != env_vars2[key]:
          self.differences[key] = (env_vars1[key], env_vars2[key])
    return self.differences

  def report(self):
    if not self.differences: 
      print("No differences found between the two environment files.")
    else:
      print("Differences found:")
      for key, (value1, value2) in self.differences.items():
        print(f"  {key}:")
        print(f"    Path 1: {value1}")
        print(f"    Path 2: {value2}")
