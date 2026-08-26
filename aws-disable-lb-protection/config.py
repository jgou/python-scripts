class ToolConfig:
  def __init__(self, profile: str, region: str, search_criteria: str, dry_run: bool):
    self.profile = profile
    self.region = region
    self.search_criteria = search_criteria
    self.dry_run = dry_run
