import enum


class ToolConfig:

  class Services(enum.Enum):
    EC2 = "ec2"
    ROUTE53 = "route53"
    S3 = "s3"

  def __init__(
    self,
    profile: str | None = None,
    regions: list[str] | None = None,
    services: list[str] | None = None,
    dry_run: bool = False,
    skip_final_snapshot: bool = False,
  ) -> None:
    self.profile: str | None = profile
    self.regions: list[str] = regions if regions is not None else []
    self.services: list[str] = services if services else [service.value for service in self.Services]
    self.dry_run: bool = dry_run
    self.skip_final_snapshot: bool = skip_final_snapshot

  @staticmethod
  def validate_services(values: list[str]) -> bool:
    valid_services = {service.value for service in ToolConfig.Services}
    invalid_services = [s for s in values if s not in valid_services]
    if invalid_services:
        raise ValueError(
            f"Invalid service(s): {', '.join(invalid_services)}. Valid options are: {', '.join(sorted(valid_services))}."
        )
    return True

  @staticmethod
  def parse_services(value: str) -> list[str]:
    services = [s.strip().lower() for s in value.split(",") if s.strip()]
    ToolConfig.validate_services(services)
    return services