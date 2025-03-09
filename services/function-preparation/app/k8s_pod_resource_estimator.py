from openai import OpenAI

# Set your API key
openai_api_key = ""

client = OpenAI(api_key=openai_api_key)

def get_k8s_pod_resources(python_code):
    """
    Sends Python code to OpenAI's GPT model and retrieves the exact recommended
    CPU and memory resources for a Kubernetes pod to run the code efficiently.
    """
    messages = [
        {
            "role": "system",
            "content": (
                "You are a Kubernetes optimization expert specializing in resource allocation for Python workloads. "
                "Analyze the given Python code and return only the necessary CPU and memory requests and limits for a Kubernetes pod. "
                "Respond in the following JSON format:\n\n"
                "{\n"
                '  "cpu_request": "<value in millicores>",\n'
                '  "cpu_limit": "<value in millicores>",\n'
                '  "memory_request": "<value in MiB>",\n'
                '  "memory_limit": "<value in MiB>"\n'
                "}\n\n"
                "Do not include any explanations or additional text."
            )
        },
        {"role": "user", "content": f"Here is the Python code:\n\n```python\n{python_code}\n```"}
    ]

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",  # Use "gpt-4o" if higher accuracy is needed
        messages=messages,
        temperature=0.3,  # Lower temperature for deterministic results
        max_tokens=100,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0
    )

    return response.choices[0].message.content  # Extract the JSON response

# Example Usage
if __name__ == "__main__":
    python_code = """
import numpy as np

# Perform a computationally heavy task
matrix = np.random.rand(1000, 1000)
result = np.linalg.inv(matrix)
print("Computation Complete!")
"""
    recommended_resources = get_k8s_pod_resources(python_code)
    print(recommended_resources)
