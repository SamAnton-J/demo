# seed_script.py
import requests
import json

# The URL of your running AI blackbox API
API_URL = "http://localhost:8000/internal/sync"

# The 10 detailed job descriptions
JOBS_DATA = [
    {
        "collection": "jobs",
        "documentId": "job_101",
        "textContent": "Senior Backend Engineer specializing in Golang (Go) to design, develop, and maintain high-performance microservices. Responsibilities include building scalable APIs, optimizing database queries with PostgreSQL, and deploying services on Kubernetes. Must have strong experience with gRPC, Docker, and CI/CD pipelines."
    },
    {
        "collection": "jobs",
        "documentId": "job_102",
        "textContent": "Experienced Frontend Developer proficient in React.js and Next.js to build modern, responsive user interfaces. You will work with TypeScript to ensure type safety and collaborate with UX/UI designers to create a seamless user experience. Experience with state management libraries like Redux or Zustand is required."
    },
    {
        "collection": "jobs",
        "documentId": "job_103",
        "textContent": "DevOps Engineer with deep knowledge of AWS cloud infrastructure and container orchestration. You will manage our production environment using Kubernetes (EKS), implement infrastructure as code with Terraform, and maintain our monitoring stack with Prometheus and Grafana. Scripting skills in Python or Bash are essential."
    },
    {
        "collection": "jobs",
        "documentId": "job_104",
        "textContent": "Data Scientist skilled in machine learning and Python to analyze large datasets and build predictive models. You should have a strong background in statistics and experience with ML frameworks like Scikit-learn, TensorFlow, or PyTorch. Familiarity with data processing tools like Pandas and Spark is a must."
    },
    {
        "collection": "jobs",
        "documentId": "job_105",
        "textContent": "Versatile Full-Stack Developer to work on both our Node.js backend and React frontend. You will be responsible for developing end-to-end features, writing RESTful APIs with Express.js, and managing our MongoDB database. This role requires strong problem-solving skills and the ability to work across the entire stack."
    },
    {
        "collection": "jobs",
        "documentId": "job_106",
        "textContent": "Seeking a motivated Junior Golang Developer eager to learn and contribute to our backend services. You will work alongside senior engineers to write clean, efficient Go code, develop unit tests, and learn about microservice architecture. A basic understanding of APIs and databases is required."
    },
    {
        "collection": "jobs",
        "documentId": "job_107",
        "textContent": "Mobile Developer with experience in React Native to build cross-platform applications for iOS and Android. You will be responsible for implementing new features, optimizing app performance, and integrating with native device APIs. Experience with mobile deployment to the App Store and Google Play is a plus."
    },
    {
        "collection": "jobs",
        "documentId": "job_108",
        "textContent": "Cloud Security Engineer to ensure the security and compliance of our AWS and Kubernetes environments. Responsibilities include vulnerability scanning, identity and access management (IAM), and implementing security best practices for our cloud infrastructure. Certifications like CISSP or AWS Security Specialty are highly valued."
    },
    {
        "collection": "jobs",
        "documentId": "job_109",
        "textContent": "AI Engineer focused on Natural Language Processing (NLP) and Large Language Models (LLMs). You will build and fine-tune models for tasks like text classification and entity extraction. Experience with Hugging Face Transformers, PyTorch, and deploying models as scalable services is required. Familiarity with vector databases like Qdrant is a bonus."
    },
    {
        "collection": "jobs",
        "documentId": "job_110",
        "textContent": "Lead Backend Engineer with a strong focus on system design and architecture. You will lead a team of Golang and Python developers, make high-level architectural decisions, and ensure the scalability and reliability of our platform. Proven experience in designing distributed systems and microservices is mandatory."
    }
]

def seed_database():
    """Iterates through the job data and sends it to the API."""
    print(f"--- Starting to seed database at {API_URL} ---")
    
    success_count = 0
    failure_count = 0
    
    for job in JOBS_DATA:
        doc_id = job["documentId"]
        print(f"  - Seeding {doc_id}...")
        
        try:
            # Send the POST request with the job data as JSON
            response = requests.post(API_URL, json=job, timeout=10)
            
            # Check for HTTP errors (like 4xx or 5xx)
            response.raise_for_status()
            
            print(f"    ✅ Success: {doc_id} seeded. Server response: {response.json()}")
            success_count += 1
        except requests.exceptions.RequestException as e:
            print(f"    ❌ FAILED to seed {doc_id}: {e}")
            failure_count += 1
            
    print("\n--- Seeding complete ---")
    print(f"Successful: {success_count}, Failed: {failure_count}")

if __name__ == "__main__":
    seed_database()