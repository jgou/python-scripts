import os

class EnvFilesCompareConfig:
  def __init__(self, paths: list[str]):
    self.paths = paths

  def validate(self):
    for path in self.paths:
      if not os.path.isfile(path):
        raise ValueError(f"Path is not a valid file: {path}")

