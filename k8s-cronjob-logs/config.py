class CronjobToolConfig:
    def __init__(self, namespace: str, cronjob: str, count: int):
        self.namespace = namespace
        self.cronjob = cronjob
        self.count = count