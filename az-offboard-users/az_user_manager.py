import json
import subprocess

import msal
import requests


class AzureUserManager:

    CLIENT_ID = "14d82eec-204b-4c2f-b7e8-296a70dab67e"  # Microsoft Graph PowerShell (public)
    SCOPES = ["User.ReadWrite.All", "Group.ReadWrite.All", "RoleManagement.ReadWrite.Directory"]
    GRAPH_BASE = "https://graph.microsoft.com/v1.0"

    def __init__(self, tenant_id, dry_run=False):
        self.tenant_id = tenant_id
        self.dry_run = dry_run
        self.authority = f"https://login.microsoftonline.com/{tenant_id}"
        self.token = None
        self.upn = None
        self.user_id = None
        self.display_name = None

    def authenticate(self):
        app = msal.PublicClientApplication(self.CLIENT_ID, authority=self.authority)
        flow = app.initiate_device_flow(scopes=self.SCOPES)

        if "user_code" not in flow:
            raise RuntimeError(f"Could not start the device flow: {flow}")

        print(flow["message"])
        result = app.acquire_token_by_device_flow(flow)

        if "access_token" not in result:
            raise RuntimeError(f"Authentication error: {result.get('error_description')}")

        self.token = result["access_token"]

    def _graph_get(self, url, params=None):
        headers = {"Authorization": f"Bearer {self.token}"}
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        return resp.json()

    def set_user(self, upn):
        self.upn = upn
        # A guest UPN contains a literal '#' (e.g. "...#EXT#@..."); if it's
        # concatenated directly into the URL, requests interprets it as the
        # fragment delimiter and truncates the query. That's why it's passed as
        # a separate param, so requests urlencodes it correctly.
        params = {
            "$filter": f"userPrincipalName eq '{upn}'",
            "$select": "id,displayName,userPrincipalName",
        }
        data = self._graph_get(f"{self.GRAPH_BASE}/users", params=params)
        values = data.get("value", [])
        if not values:
            self.user_id = None
            self.display_name = None
            return
        self.user_id = values[0]["id"]
        self.display_name = values[0]["displayName"]

    def block_signin(self):
        if self.dry_run:
            print(f"  [dry-run] Block sign-in for the user '{self.upn}'")
            return
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        resp = requests.patch(f"{self.GRAPH_BASE}/users/{self.user_id}", headers=headers,
                               data=json.dumps({"accountEnabled": False}))
        resp.raise_for_status()
        print("  Sign-in blocked.")

    def revoke_sessions(self):
        if self.dry_run:
            print(f"  [dry-run] Revoke sessions for the user '{self.upn}'")
            return
        headers = {"Authorization": f"Bearer {self.token}"}
        resp = requests.post(f"{self.GRAPH_BASE}/users/{self.user_id}/revokeSignInSessions", headers=headers)
        resp.raise_for_status()
        print("  Sessions revoked.")

    def remove_from_all_groups(self):
        data = self._graph_get(f"{self.GRAPH_BASE}/users/{self.user_id}/memberOf")
        groups = [g for g in data.get("value", []) if g.get("@odata.type") == "#microsoft.graph.group"]
        if not groups:
            print("  No groups assigned.")
            return
        headers = {"Authorization": f"Bearer {self.token}"}
        for g in groups:
            gid, gname = g["id"], g.get("displayName", g["id"])
            if self.dry_run:
                print(f"  [dry-run] would remove from group '{gname}'")
                continue
            # Dynamic groups can't be edited manually: Graph will return an error, which we catch.
            resp = requests.delete(f"{self.GRAPH_BASE}/groups/{gid}/members/{self.user_id}/$ref", headers=headers)
            if resp.status_code in (204, 200):
                print(f"  Removed from group '{gname}'.")
            else:
                print(f"  Could not remove from group '{gname}' (is it dynamic?): {resp.status_code} {resp.text[:200]}")

    def remove_directory_roles(self):
        data = self._graph_get(f"{self.GRAPH_BASE}/users/{self.user_id}/memberOf")
        roles = [g for g in data.get("value", []) if g.get("@odata.type") == "#microsoft.graph.directoryRole"]
        if not roles:
            print("  No directory roles assigned.")
            return
        headers = {"Authorization": f"Bearer {self.token}"}
        for r in roles:
            rid, rname = r["id"], r.get("displayName", r["id"])
            if self.dry_run:
                print(f"  [dry-run] would remove directory role '{rname}'")
                continue
            resp = requests.delete(f"{self.GRAPH_BASE}/directoryRoles/{rid}/members/{self.user_id}/$ref", headers=headers)
            if resp.status_code in (204, 200):
                print(f"  Directory role '{rname}' removed.")
            else:
                print(f"  Could not remove role '{rname}': {resp.status_code} {resp.text[:200]}")

    def remove_azure_rbac_roles(self):
        """Uses Azure CLI (already logged in) to list and remove RBAC assignments at ALL scopes."""
        try:
            result = subprocess.run(
                ["az", "role", "assignment", "list", "--assignee", self.upn, "--all", "-o", "json"],
                capture_output=True, text=True, check=True,
            )
        except FileNotFoundError:
            print("  Azure CLI not found on PATH; skipping this step or install it.")
            return
        except subprocess.CalledProcessError as e:
            print(f"  Error querying az role assignment list: {e.stderr}")
            return

        assignments = json.loads(result.stdout) if result.stdout.strip() else []
        if not assignments:
            print("  No Azure RBAC assignments.")
            return

        for a in assignments:
            role_name = a.get("roleDefinitionName")
            scope = a.get("scope")
            if self.dry_run:
                print(f"  [dry-run] would remove RBAC role '{role_name}' at scope '{scope}'")
                continue
            try:
                subprocess.run(
                    ["az", "role", "assignment", "delete", "--assignee", self.upn,
                     "--role", role_name, "--scope", scope],
                    capture_output=True, text=True, check=True,
                )
                print(f"  RBAC role '{role_name}' removed at scope '{scope}'.")
            except subprocess.CalledProcessError as e:
                print(f"  Could not remove RBAC role '{role_name}' at '{scope}': {e.stderr}")
