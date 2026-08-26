import argparse
from config import EnvFilesCompareConfig
from compare import EnvFilesCompare


def main():
  arg_parser = argparse.ArgumentParser(description="Environment Files Compare")
  arg_parser.add_argument("--paths", nargs='+', type=str, help="Paths to multiple environment files for comparison.")
  args = arg_parser.parse_args()
  print(f"Comparing environment files:\n  Path 1: {args.paths[0]}\n  Path 2: {args.paths[1]}")

  config = EnvFilesCompareConfig(args.paths)
  config.validate()
  print("Validation successful. Proceeding with comparison...")

  comparer = EnvFilesCompare(config)
  comparer.compare()
  comparer.report()
