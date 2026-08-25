import os
import yaml

class DeploymentValidator:
  def __init__(self, config):
    self.config = config

  def validate(self):
    self.config.validate()

    for entry in os.scandir(self.config.getPath()):
      if entry.is_file() and entry.name.endswith(".yaml"):
        self.__validate_file(entry.path)
        
  def __validate_file(self, file_path):
    try:
      with open(file_path, 'r') as file:
        yaml_data = yaml.safe_load(file)

        if yaml_data is None:
          print(f"File {file_path} is empty or not a valid YAML file.")
          return

        self.validated = self.__check_content(yaml_data)
    except yaml.YAMLError as e:
      print(f"YAML error in file {file_path}: {e}")
    except Exception as e:
      print(f"Failed to read file {file_path}: {e}")
  
  def __check_content(self, data):
    if not isinstance(data, dict) or data.get("kind") != "Deployment":
      print(f"YAML content in file is not a dictionary or not a Deployment.")
      return False

    containers = data.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])

    for container in containers:
      if not isinstance(container, dict):
        print(f"Container definition is not a dictionary.")
        return False

      if "readinessProbe" not in container or "livenessProbe" not in container:
        print(f"Container {container.get('name', 'unknown')} does not have readiness or liveness probes defined.")
        return False

      resources = container.get("resources", {})
      if "limits" not in resources or "requests" not in resources:
        print(f"Container {container.get('name', 'unknown')} does not have resource limits or requests defined.")
        return False
    
    return True

