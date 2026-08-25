import os
import yaml

class DeploymentValidatorConfig:
  def __init__(self, path):
    self.path = os.path.join(os.getcwd(), path)
    self.__load_validation_fields()

  def validate(self):
    # Placeholder for validation logic
    print(f"Validating deployments in {self.path}")
    # Here you would add the actual validation logic for Kubernetes deployment YAML files.

  def get_path(self):
    return self.path

  def __load_validation_fields(self):
    config_file = os.path.join(os.path.dirname(__file__), "config", "validation_fields.yaml")

    try:
      with open(config_file, 'r') as file:
        config = yaml.safe_load(file)
        self.required_fields = config.get("required_fields", [])
    except Exception as e:
      print(f"Failed to load validation fields from {config_file}: {e}")


  def get_required_fields(self):
    return self.required_fields

