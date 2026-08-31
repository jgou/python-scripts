import msal
import requests
import csv

class AzureUsers:

  CLIENT_ID = "14d82eec-204b-4c2f-b7e8-296a70dab67e"  # Microsoft Graph PowerShell public client id (for testing only)
  SCOPES = ["User.Read.All"]
  GRAPH_BASE = "https://graph.microsoft.com/v1.0"

  def __init__(self, tenant_id):
    self.tenant_id = tenant_id
    self.authority = f"https://login.microsoftonline.com/{tenant_id}"
    self.token = None

  def authenticate(self):
    """Authenticates via device code flow and returns the access token."""
    app = msal.PublicClientApplication(self.CLIENT_ID, authority=self.authority)

    flow = app.initiate_device_flow(scopes=self.SCOPES)
    if "user_code" not in flow:
        raise RuntimeError(f"Could not start the device flow: {flow}")

    print(flow["message"])  # instructions: go to microsoft.com/devicelogin and paste the code
    result = app.acquire_token_by_device_flow(flow)

    if "access_token" not in result:
        raise RuntimeError(f"Authentication error: {result.get('error_description')}")

    self.token = result["access_token"]

  def get_all_users(self):
    """Walks Graph's pagination and returns all users."""
    headers = {"Authorization": f"Bearer {self.token}"}
    select_fields = (
        "id,displayName,userPrincipalName,mail,jobTitle,department,"
        "accountEnabled,userType,createdDateTime,onPremisesSyncEnabled"
    )
    url = f"{self.GRAPH_BASE}/users?$select={select_fields}&$top=999"

    users = []
    while url:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        users.extend(data.get("value", []))
        url = data.get("@odata.nextLink")  # Graph handles pagination via this field

    return users

  @staticmethod
  def get_enabled_users(users):
    """Returns a list of UserPrincipalName for enabled users."""
    return [user for user in users if user.get("accountEnabled")]

  @staticmethod
  def filter_users(users, substring):
    substring = substring.lower()
    return [u for u in users if substring in (u.get("userPrincipalName") or "").lower()]

  @staticmethod
  def pretty_print(users):
    print(f"\n{'DisplayName':30} {'UserPrincipalName':35} {'Enabled':8} {'Department'}")
    print("-" * 100)
    for u in sorted(users, key=lambda x: x.get("displayName") or ""):
      print(
          f"{(u.get('displayName') or '')[:30]:30} "
          f"{(u.get('userPrincipalName') or '')[:35]:35} "
          f"{str(u.get('accountEnabled')):8} "
          f"{u.get('department') or ''}"
      )

  @staticmethod
  def export(file_path, users):
    fieldnames = [
        "id", "displayName", "userPrincipalName", "mail", "jobTitle",
        "department", "accountEnabled", "userType", "createdDateTime",
        "onPremisesSyncEnabled",
    ]
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for u in users:
            writer.writerow({k: u.get(k) for k in fieldnames})
    print(f"\nExported to: {file_path}")
