import os

class EnvFilesCompareConfig:
  def __init__(self, path1: str, path2: str):
    self.path1 = path1
    self.path2 = path2

  def validate(self):
    if not os.path.isfile(self.path1):
      raise ValueError(f"Path 1 is not a valid file: {self.path1}")
    if not os.path.isfile(self.path2):
      raise ValueError(f"Path 2 is not a valid file: {self.path2}")
