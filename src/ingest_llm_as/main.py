from fastapi import FastAPI

app = FastAPI(
    title="InGest-LLM.as",
    description="A microservice for ingesting data into the ApexSigma ecosystem."
)

@app.get("/")
def read_root():
    """
    Root endpoint that returns a welcome message.
    """
    return {"message": "Welcome to the InGest-LLM.as service!"}

@app.get("/health")
def health_check():
    """
    Simple health check endpoint.
    """
    return {"status": "ok"}