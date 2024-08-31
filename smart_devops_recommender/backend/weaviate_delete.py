import weaviate

# Initialize the Weaviate client
client = weaviate.Client("http://localhost:8080")  # Replace with your Weaviate instance URL

# Define the class name you want to delete
class_name = "DevOpsPrompts_v2"  # Replace with the name of the class you want to delete

# Function to delete a class
def delete_class(client, class_name):
    try:
        # Check if the class exists
        if client.schema.exists(class_name):
            # Delete the class
            client.schema.delete_class(class_name)
            print(f"Class '{class_name}' deleted successfully.")
        else:
            print(f"Class '{class_name}' does not exist.")
    except Exception as e:
        print(f"An error occurred while deleting the class: {e}")

# Call the function to delete the class
delete_class(client, class_name)
