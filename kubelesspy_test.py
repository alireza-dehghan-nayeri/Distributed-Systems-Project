import random
import string
from locust import HttpUser, task, between

# Store registered function IDs
registered_function_ids = set()


class FunctionUser(HttpUser):
    """Simulates users registering and triggering functions."""

    host = "http://195.148.31.43:30080"
    wait_time = between(3, 10)  # Random wait time between tasks

    def generate_function_name(self):
        """Generate a unique function name."""
        return "test_function_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=6))

    def on_start(self):
        """Ensure each user registers at least one function."""
        self.register_function()

    @task(3)  # Runs more frequently
    def trigger_function(self):
        """Randomly trigger a registered function."""
        if not registered_function_ids:
            print("No functions registered yet. Skipping trigger.")
            return

        function_id = random.choice(list(registered_function_ids))
        trigger_payload = {"function_id": function_id}

        response = self.client.post(
            url="/function-trigger/trigger/",
            json=trigger_payload,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            print(f"Function {function_id} triggered successfully.")
        else:
            print(f"Failed to trigger function {function_id}: {response.status_code} - {response.text}")

    @task(1)  # Runs less frequently
    def register_function(self):
        """Registers a new function and stores the returned function ID."""
        function_name = self.generate_function_name()

        register_payload = {
            "name": function_name,
            "code": """def handler():
    \"\"\"Sample function to be executed dynamically.\"\"\"
    print(\"Hello from the dynamically executed function!\")
    result = sum(range(1, 11))
    print(f\"Computed result: {result}\")
    return result""",
            "requirements": "numpy"
        }

        response = self.client.post(
            url="/function-registration/register/",
            json=register_payload,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            function_id = response.json().get("id")
            if function_id:
                registered_function_ids.add(function_id)
                print(f"Function {function_name} registered with ID: {function_id}")
        else:
            print(f"Failed to register function {function_name}: {response.status_code} - {response.text}")

