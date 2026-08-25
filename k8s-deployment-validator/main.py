from argparse import ArgumentParser
from config import DeploymentValidatorConfig
from validator import DeploymentValidator


def main():
  arg_parser = ArgumentParser(description="Kubernetes Deployment Validator")
  arg_parser.add_argument("--path", type=str, required=True, help="Path to folder where the Kubernetes deployment YAML files are.")
  args = arg_parser.parse_args()
  print(f"Validating Kubernetes deployment YAML files in path: {args.path}")

  config = DeploymentValidatorConfig(args.path)
  config.validate()

  validator = DeploymentValidator(config)
  validator.validate()


