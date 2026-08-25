import os

class DeploymentValidatorConfig:
  def __init__(self, path):
    self.path = os.path.join(os.getcwd(), path)

  def validate(self):
    # Placeholder for validation logic
    print(f"Validating deployments in {self.path}")
    # Here you would add the actual validation logic for Kubernetes deployment YAML files.

  def getPath(self):
    return self.path
