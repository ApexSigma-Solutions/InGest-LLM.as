import os
from langfuse import Langfuse
from langfuse.decorators import observe

# This script tests the connection to Langfuse using the @observe decorator

# Get credentials from environment variables
public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
secret_key = os.environ.get("LANGFUSE_SECRET_KEY")
host = os.environ.get("LANGFUSE_HOST")

# Check if all credentials are set
if not all([public_key, secret_key, host]):
    print("Error: Langfuse environment variables not set.")
    exit(1)

# Initialize Langfuse client
try:
    langfuse = Langfuse(
        public_key=public_key,
        secret_key=secret_key,
        host=host
    )
    print("Langfuse client initialized successfully.")
except Exception as e:
    print(f"Error initializing Langfuse client: {e}")
    exit(1)

@observe()
def my_llm_feature():
    print("Executing my_llm_feature")

# Test the connection by calling the decorated function
try:
    my_llm_feature()
    print("Successfully executed decorated function.")
except Exception as e:
    print(f"Error executing decorated function: {e}")
    exit(1)

# Flush the client to ensure the event is sent
langfuse.flush()
print("Langfuse client flushed.")
