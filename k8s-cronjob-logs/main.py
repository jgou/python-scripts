import argparse
import config as CronjobToolConfig
import processer as CronJobKubernetesProcessor

def main():
    parser = argparse.ArgumentParser(description="Fetch logs from the last N cronjob Job executions.")
    parser.add_argument("--namespace", default="redis-migration")
    parser.add_argument("--cronjob", default="riot-compare-cron")
    parser.add_argument("--count", type=int, default=10)
    args = parser.parse_args()

    config = CronjobToolConfig.CronjobToolConfig(
        namespace=args.namespace,
        cronjob=args.cronjob,
        count=args.count
    )

    processor = CronJobKubernetesProcessor.CronJobKubernetesProcessor(config)
    logs = processor.fetch_logs()
    print(logs)