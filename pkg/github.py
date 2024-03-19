import requests
import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
REPO_OWNER = os.getenv('REPO_OWNER')

class Github:

  def search_pull_requests(self, repo_name:str, status:str, label:str='') -> list:
    print(f"Searching for pull requests with status: {status} and label: {label}")
    repo_name = f"{REPO_OWNER}/{repo_name}"
    access_token = GITHUB_TOKEN
    query = f"is:pr is:{status} {label}"
    encoded_query = requests.utils.quote(query)

    url = f"https://api.github.com/search/issues?q={encoded_query}+repo:{repo_name}"
    git_url = f"https://api.github.com/repos/{repo_name}/pulls"

    print(f"Fetching data from: {url}")

    headers = {
      'Authorization': f"token {access_token}",
      'Accept': "application/vnd.github.v3+json"
    }

    response = requests.get(url, headers=headers)

    commits_sha = []

    if response.status_code == 200:
      pull_requests = response.json()['items']
      pull_requests = sorted(pull_requests, key=lambda pr: pr['number'], reverse=False)
      pull_requests_with_commits = []

      for pr in pull_requests:
        pr_title = pr['title']
        pr_number = pr['number']

        commits_url = f"{git_url}/{pr_number}/commits"
        commits_response = requests.get(commits_url, headers=headers)

        if commits_response.status_code == 200:
          commits_data = commits_response.json()
          pull_request_commits = []
          for commit in commits_data:
            pull_request_commits.append({
              'author': commit['commit']['author']['name'],
              'date': commit['commit']['author']['date'],
              'commit': commit['sha'],
            })
            commits_sha.append(commit['sha'])
          pull_requests_with_commits.append({
            'title': pr_title,
            'url': pr['html_url'],
            'commits': pull_request_commits
          })

      pull_requests_with_commits.append({
        'commits_summary': commits_sha,
      })

      return pull_requests_with_commits
    else:
      print(f"Failed to fetch data. Status code: {response.status_code}")
      return []