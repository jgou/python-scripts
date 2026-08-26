class EnvFileLoader:
  @staticmethod
  def load_env_file (filePath: str) -> dict:
    env_vars = {}
    with open(filePath, 'r') as file:
      for line in file:
        line = line.strip()
        if line and not line.startswith('#'):
          var_name, var_value = line.split('=', 1)
          env_vars[var_name.strip()] = var_value.strip()
    return env_vars
