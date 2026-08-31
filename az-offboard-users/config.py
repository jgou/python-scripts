class ConfigTool:
    def __init__(self, upns=None, upns_file=None, dry_run=False):
        self.upns = upns or []
        self.upns_file = upns_file
        self.dry_run = dry_run

    def load_upns(self):
        if self.upns_file:
            with open(self.upns_file, "r", encoding="utf-8") as f:
                self.upns.extend(line.strip() for line in f if line.strip())
        return self.upns