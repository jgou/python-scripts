import os
import yaml

class DeploymentValidator:
  def __init__(self, config):
    self.config = config

  def validate(self):
    self.config.validate()

    for entry in os.scandir(self.config.get_path()):
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

  def __get_nested_value(self, obj, item):
    keys = item.split('.')
    current = obj
    for key in keys:
      if isinstance(current, dict) and key in current:
        current = current[key]
      else:
        return None
    return current
  
  def __check_content(self, data):
    if not isinstance(data, dict) or data.get("kind") != "Deployment":
      print(f"YAML content in file is not a dictionary or not a Deployment.")
      return False

    containers = data.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])

    for container in containers:
      if not isinstance(container, dict):
        print(f"Container definition is not a dictionary.")
        return False

      required_fields = self.config.get_required_fields()
      for field in required_fields:
        if self.__get_nested_value(container, field) is None:
          print(f"Container {container.get('name', 'unknown')} does not have {field} defined.")
          return False

    return True

