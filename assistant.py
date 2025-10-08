import argparse
from dotenv import load_dotenv
import os
from pydantic import BaseModel, Field, ValidationError
from typing import Optional, List
import json
import requests
import time
from openai import OpenAI
import csv

# Load environment variables from .env file
load_dotenv()

# Pydantic models supporting the project
class JobSearchConfig(BaseModel):
    # Source: https://docs.brightdata.com/api-reference/web-scraper-api/social-media-apis/linkedin#discover-by-keyword
    location: str
    keyword: Optional[str] = None
    country: Optional[str] = None
    time_range: Optional[str] = None
    job_type: Optional[str] = None
    experience_level: Optional[str] = None
    remote: Optional[str] = None
    company: Optional[str] = None
    selective_search: Optional[bool] = Field(default=False)
    jobs_to_not_include: Optional[List[str]] = Field(default_factory=list)
    location_radius: Optional[str] = None
    # Additional fields
    profile_summary: str  # Candidate's profile summary for AI scoring
    desired_job_summary: str  # Description of the desired job for AI scoring

class JobScore(BaseModel):
    job_posting_id: str
    score: int = Field(..., ge=0, le=100)
    comment: str

class JobScoresResponse(BaseModel):
    scores: List[JobScore]

def parse_cli_args():
    # Parse command-line arguments for config and runtime options
    parser = argparse.ArgumentParser(description="LinkedIn Job Hunting Assistant")
    parser.add_argument("--config_file", type=str, default="config.json", help="Path to config JSON file")
    parser.add_argument("--jobs_number", type=int, default=20, help="Limit the number of jobs returned by Bright Data Scraper API")
    parser.add_argument("--batch_size", type=int, default=5, help="Number of jobs to score in each batch")
    parser.add_argument("--output_csv", type=str, default="jobs_scored.csv", help="Output CSV filename")

    return parser.parse_args()

def load_env_vars():
    # Read required API keys from environment and verify presence
    openai_api_key = os.getenv("OPENAI_API_KEY")
    brightdata_api_key = os.getenv("BRIGHT_DATA_API_KEY")

    missing = []
    if not openai_api_key:
        missing.append("OPENAI_API_KEY")
    if not brightdata_api_key:
        missing.append("BRIGHT_DATA_API_KEY")
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            "Please set them in your .env or environment."
        )

    return openai_api_key, brightdata_api_key

def load_and_validate_config(filename: str) -> JobSearchConfig:
    # Load JSON config file
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file '{filename}' not found.")

    try:
        # Deserialize the input JSON data to a JobSearchConfig instance
        config = JobSearchConfig(**data)
    except ValidationError as e:
        raise ValueError(f"Config deserialization error:\n{e}")

    return config

def trigger_and_poll_linkedin_jobs(config: JobSearchConfig, brightdata_api_key: str, jobs_number: int, polling_timeout=10):
    # Trigger the Bright Data LinkedIn job search
    url = "https://api.brightdata.com/datasets/v3/trigger"
    headers = {
        "Authorization": f"Bearer {brightdata_api_key}",
        "Content-Type": "application/json",
    }
    params = {
        "dataset_id": "gd_lpfll7v5hcqtkxl6l", # Bright Data "Linkedin job listings information - discover by keyword" dataset ID
        "include_errors": "true",
        "type": "discover_new",
        "discover_by": "keyword",
        "limit_per_input": str(jobs_number),
    }

    # Prepare payload for Bright Data API based on user config
    data = [{
        "location": config.location,
        "keyword": config.keyword or "",
        "country": config.country or "",
        "time_range": config.time_range or "",
        "job_type": config.job_type or "",
        "experience_level": config.experience_level or "",
        "remote": config.remote or "",
        "company": config.company or "",
        "selective_search": config.selective_search,
        "jobs_to_not_include": config.jobs_to_not_include or "",
        "location_radius": config.location_radius or "",
    }]

    response = requests.post(url, headers=headers, params=params, json=data)
    if response.status_code != 200:
        raise RuntimeError(f"Trigger request failed: {response.status_code} - {response.text}")

    snapshot_id = response.json().get("snapshot_id")
    if not snapshot_id:
        raise RuntimeError("No snapshot_id returned from Bright Data trigger.")

    print(f"LinkedIn job search triggered! Snapshot ID: {snapshot_id}")

    # Poll snapshot endpoint until data is ready or timeout
    snapshot_url = f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}?format=json"
    headers = {"Authorization": f"Bearer {brightdata_api_key}"}

    print(f"Polling snapshot for ID: {snapshot_id}")

    while True:
        snap_resp = requests.get(snapshot_url, headers=headers)
        if snap_resp.status_code == 200:
            # Snapshot ready: return job postings JSON data
            print("Snapshot is ready")

            return snap_resp.json()
        elif snap_resp.status_code == 202:
            # Snapshot not ready yet: wait and retry
            print(f"Snapshot not ready yet. Retrying in {polling_timeout} seconds...")
            time.sleep(polling_timeout)
        else:
            raise RuntimeError(f"Snapshot polling failed: {snap_resp.status_code} - {snap_resp.text}")

# Initialize OpenAI client
client = OpenAI()

def score_jobs_batch(jobs_batch: List[dict], profile_summary: str, desired_job_summary: str) -> List[JobScore]:
    # Construct prompt for AI to score job matches based on candidate profile
    prompt = f"""
        "You are an expert recruiter. Given the following candidate profile:\n"
        "{profile_summary}\n\n"
        "Desired job description:\n{desired_job_summary}\n\n"
        "Score each job posting accurately from 0 to 100 on how well it matches the profile and desired job.\n"
        "For each job, add a short comment (max 50 words) explaining the score and match quality.\n"
        "Return an array of objects with keys 'job_posting_id', 'score', and 'comment'.\n\n"
        "Jobs:\n{json.dumps(jobs_batch)}\n"
    """
    messages = [
        {"role": "system", "content": "You are a helpful job scoring assistant."},
        {"role": "user", "content": prompt},
    ]

    # Use OpenAI API to parse structured response into JobScoresResponse model
    response = client.responses.parse(
        model="gpt-5-mini",
        input=messages,
        text_format=JobScoresResponse,
    )

    # Return list of scored jobs
    return response.output_parsed.scores

def extend_jobs_with_scores(jobs: List[dict], all_scores: List[JobScore]) -> List[dict]:
    # Where to store the enriched data
    extended_jobs = []

    # Combine original jobs with AI scores and comments
    for score_obj in all_scores:
        matched_job = None
        for job in jobs:
            if job.get("job_posting_id") == score_obj.job_posting_id:
                matched_job = job
                break
        if matched_job:
            job_with_score = dict(matched_job)
            job_with_score["ai_score"] = score_obj.score
            job_with_score["ai_comment"] = score_obj.comment
            extended_jobs.append(job_with_score)

    # Sort extended jobs by AI score (highest first)
    extended_jobs.sort(key=lambda j: j["ai_score"], reverse=True)
    return extended_jobs

def export_extended_jobs(extended_jobs: List[dict], output_csv: str):
    # Dynamically get the field names from the first element in the array
    fieldnames = list(extended_jobs[0].keys())
    with open(output_csv, mode="w", newline="", encoding="utf-8") as csvfile:
         # Write extended job data with AI scores to CSV
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for job in extended_jobs:
            writer.writerow(job)

    print(f"Exported {len(extended_jobs)} jobs to {output_csv}")

def print_top_jobs(extended_jobs: List[dict], top: int = 3):
    print(f"\n*** Top {top} job matches ***")
    for job in extended_jobs[:3]:
        print(f"URL: {job.get('url', 'N/A')}")
        print(f"Title: {job.get('job_title', 'N/A')}")
        print(f"AI Score: {job.get('ai_score')}")
        print(f"AI Comment: {job.get('ai_comment', 'N/A')}")
        print("-" * 40)

def main():
    # Get runtime parameters from CLI
    args = parse_cli_args()

    try:
         # Load API keys from environment
        _, brightdata_api_key = load_env_vars()

         # Load job search config file
        config = load_and_validate_config(args.config_file)

        # Fetch jobs
        jobs_data = trigger_and_poll_linkedin_jobs(config, brightdata_api_key, args.jobs_number)

        print(f"{len(jobs_data)} jobs found!")
    except Exception as e:
        print(f"[Error] {e}")
        return

    all_scores = []
    # Process jobs in batches to avoid overloading API and to handle large datasets
    for i in range(0, len(jobs_data), args.batch_size):
        batch = jobs_data[i : i + args.batch_size]

        print(f"Scoring batch {i // args.batch_size + 1} with {len(batch)} jobs...")

        scores = score_jobs_batch(batch, config.profile_summary, config.desired_job_summary)
        all_scores.extend(scores)

        time.sleep(1) # To avoid triggering API rate limits

    # Merge scores into scraped jobs
    extended_jobs = extend_jobs_with_scores(jobs_data, all_scores)

    # Save results to CSV
    export_extended_jobs(extended_jobs, args.output_csv)

    # Print top job matches with key info for quick review
    print_top_jobs(extended_jobs)

if __name__ == "__main__":
    main()
