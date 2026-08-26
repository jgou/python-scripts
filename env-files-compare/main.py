import argparse
from config import EnvFilesCompareConfig
from compare import EnvFilesCompare


def main():
  arg_parser = argparse.ArgumentParser(description="Environment Files Compare")
  arg_parser.add_argument("--path1", type=str, required=True, help="Path to the first environment file.")
  arg_parser.add_argument("--path2", type=str, required=True, help="Path to the second environment file.")
  args = arg_parser.parse_args()
  print(f"Comparing environment files:\n  Path 1: {args.path1}\n  Path 2: {args.path2}")

  config = EnvFilesCompareConfig(args.path1, args.path2)
  config.validate()
  print("Validation successful. Proceeding with comparison...")

  comparer = EnvFilesCompare(config)
  comparer.compare()
  comparer.report()
