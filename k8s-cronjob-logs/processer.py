import subprocess
import json
import sys

class CronJobKubernetesProcessor:
    def __init__(self, config):
        self.config = config

    @staticmethod
    def run_kubectl(args):
      """Run a kubectl command and return stdout, raising on failure."""
      result = subprocess.run(
          ["kubectl"] + args,
          capture_output=True,
          text=True,
      )
      if result.returncode != 0:
          print(f"kubectl command failed: {' '.join(args)}", file=sys.stderr)
          print(result.stderr, file=sys.stderr)
          sys.exit(1)
      return result.stdout

    def __get_job_for_cronjob(self):
        """Return the last `count` Jobs whose name starts with <cronjob_name>-,
            sorted by creation time (most recent first)."""
        raw = CronJobKubernetesProcessor.run_kubectl(["get", "jobs", "-n", self.config.namespace, "-o", "json"])
        jobs = json.loads(raw)["items"]
        
        matching = [
          j for j in jobs
                if j["metadata"]["name"].startswith(f"{self.config.cronjob}-")
                or j["metadata"]["name"].startswith(f"{self.config.cronjob}")
            ]
        
        matching.sort(
            key=lambda j: j["metadata"]["creationTimestamp"],
            reverse=True,
        )
        return matching[:self.config.count]

    def get_pod_for_job(self, job_name):
        """Return the pod name associated with a given Job."""
        raw = CronJobKubernetesProcessor.run_kubectl([
            "get", "pods", "-n", self.config.namespace,
            "-l", f"job-name={job_name}",
            "-o", "json",
        ])
        pods = json.loads(raw)["items"]
        if not pods:
            return None
        # There should normally be exactly one pod per Job run (restartPolicy: Never)
        return pods[0]["metadata"]["name"]

    def __get_pod_logs(self, pod_name):
        return CronJobKubernetesProcessor.run_kubectl(["logs", "-n", self.config.namespace, pod_name])

    def fetch_logs(self):
        jobs = self.__get_job_for_cronjob()

        sections = []
        for job in jobs:
            job_name = job["metadata"]["name"]
            pod_name = self.get_pod_for_job(job_name)
            if pod_name is None:
                sections.append(f"=== {job_name} (no pod found) ===")
                continue
            pod_logs = self.__get_pod_logs(pod_name)
            sections.append(f"=== {job_name} (pod {pod_name}) ===\n{pod_logs}")
        return "\n\n".join(sections)
