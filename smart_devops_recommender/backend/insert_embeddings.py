import openai
import weaviate
import os
from utils import generate_embedding

# Initialize the OpenAI client
openai.api_key = os.getenv('OPENAI_KEY')  # Replace with your actual OpenAI API key

# Initialize the Weaviate client
client = weaviate.Client("http://localhost:8080")  # Replace with your Weaviate instance URL

# Define the schema
schema = {
    "classes": [
        {
            "class": "DevOpsPrompts_v2",
            "properties": [
                {
                    "name": "prompt",
                    "dataType": ["text"]
                },
                {
                    "name": "response",
                    "dataType": ["text"]
                },
                {
                    "name": "retrievalCount",
                    "dataType": ["int"]
                }
            ]
        }

    ]
}

# Create the schema
client.schema.create(schema)

# Prepare the DevOps-related prompt-response pairs
data = [
    {"prompt": "How do you set up a CI/CD pipeline?", "response": "To set up a CI/CD pipeline, you need to use tools like Jenkins, GitLab CI, or GitHub Actions. Start by defining your build and deployment stages in a configuration file."},
    {"prompt": "What is Infrastructure as Code (IaC)?", "response": "Infrastructure as Code (IaC) is the practice of managing and provisioning computing infrastructure using machine-readable configuration files. Tools like Terraform and Ansible are commonly used for IaC."},
    {"prompt": "How do you monitor a Kubernetes cluster?", "response": "To monitor a Kubernetes cluster, you can use tools like Prometheus, Grafana, and the Kubernetes Dashboard. These tools help you track the health and performance of your cluster."},
    {"prompt": "What is the purpose of Docker?", "response": "Docker is a platform that allows you to automate the deployment of applications inside lightweight, portable containers. It helps ensure consistency across different environments."},
    {"prompt": "How do you handle secrets in DevOps?", "response": "In DevOps, secrets management can be handled using tools like HashiCorp Vault, AWS Secrets Manager, or Kubernetes Secrets. These tools help securely store and manage sensitive information."},
    {
        "prompt": "How do you implement blue-green deployments?",
        "response": "Blue-green deployments involve running two identical production environments, one active (blue) and one idle (green). Deploy the new version of the application to the green environment, test it, and then switch traffic to the green environment. If any issues arise, you can quickly switch back to the blue environment. This approach minimizes downtime and reduces the risk of deployment failures."
    },
    {
        "prompt": "What is the role of configuration management in DevOps?",
        "response": "Configuration management involves maintaining the consistency of a system's performance and functionality by managing its configuration. Tools like Ansible, Puppet, and Chef are commonly used for configuration management. These tools automate the deployment and management of configurations, ensure consistency across environments, and enable version control for configuration changes."
    },
    {
        "prompt": "How do you ensure high availability in a cloud environment?",
        "response": "To ensure high availability in a cloud environment, use strategies such as load balancing, auto-scaling, and multi-region deployments. Implement redundancy for critical components, use managed services with built-in high availability, and monitor the system for any issues. Design the architecture to handle failures gracefully and ensure that data is backed up and recoverable."
    },
    {
        "prompt": "What is the importance of logging and monitoring in DevOps?",
        "response": "Logging and monitoring are crucial in DevOps for maintaining the health and performance of applications and infrastructure. Logging provides insights into application behavior and helps diagnose issues, while monitoring tracks the performance and availability of systems. Use tools like ELK stack, Prometheus, and Grafana to collect, analyze, and visualize logs and metrics."
    }
    # Add more prompt-response pairs as needed
]


# Function to generate embeddings using OpenAI

# Use batch import to add data with embeddings
with client.batch as batch:
    for i, d in enumerate(data):
        print(f"Importing prompt-response pair: {i+1}")
        combined_text = f"Prompt: {d['prompt']} Response: {d['response']}"
        embedding = generate_embedding(combined_text)
        properties = {
            "prompt": d["prompt"],
            "response": d["response"]
        }
        batch.add_data_object(
            data_object=properties,
            class_name="DevOpsPrompts",
            vector=embedding
        )

print("Data inserted successfully.")

# Query the data to verify vector generation
result = client.query.get("DevOpsPrompts", ["prompt", "response", "_additional { vector }"]).do()

# Print the results
for item in result['data']['Get']['DevOpsPrompts']:
    print(f"Prompt: {item['prompt']}")
    print(f"Response: {item['response']}")
    print(f"Vector: {item['_additional']['vector']}\n")
