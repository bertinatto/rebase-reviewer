# git_llm_reviewer.py

import os
import sys
import json
import re
import subprocess
import google.generativeai as genai
from github import Github, UnknownObjectException, GithubException, Auth
import questionary
from reporter import Reporter
from colorprint import print_header, print_warning, print_fail, print_info, colorize

# --- Configuration ---
GEMINI_MODEL = 'gemini-2.5-pro'

custom_style = questionary.Style([
    ('highlighted', 'bg:#44475a fg:#f8f8f2 bold'),
    ('pointer', 'fg:#50fa7b bold'),                  # Pointer with green color
    ('text', 'fg:#f8f8f2'),                         # Regular text
    ('answer', 'fg:#50fa7b bold'),                  # Answer text
])

# Custom style specifically for questionary selects with highlighting
select_style = questionary.Style([
    ('highlighted', 'bg:#5555ff fg:#ffffff bold'),   # Blue background for selected item
    ('pointer', 'fg:#ffff55 bold'),                  # Yellow pointer
    ('text', ''),                                    # Default text
    ('answer', 'fg:#50fa7b bold'),                   # Green for final answer
])

def run_git_command(command, check=True):
    """Executes a Git command and returns its output."""
    result = subprocess.run(
        command,
        check=check,
        capture_output=True,
        text=True,
        encoding='utf-8'
    )
    return result.stdout.strip()


def get_commits(branch, start_commit=None, formatted=False, limit=1000, reverse=True):
    """
    Gets a list of commits from a start_commit to the tip of a branch.
    If formatted is True, returns a list of "hash message" strings.
    """
    log_format = "--pretty=format:%H|||%s"
    command_parts = ["git", "log", log_format, f"--max-count={limit}", "--no-merges"]

    if reverse:
        command_parts.append("--reverse")
    
    if start_commit:
        command_parts.append(f"{start_commit}^..{branch}")
    else:
        command_parts.append(branch)
        
    output = run_git_command(command_parts)
    
    if not output:
        return []
        
    commits = []
    for line in output.split('\n'):
        parts = line.split('|||', 1)
        if len(parts) == 2:
            commit_hash = parts[0]
            message = parts[1]
            if formatted:
                commits.append(f"{commit_hash} {message}")
            else:
                commits.append({"hash": commit_hash, "message": message})
    return commits


def get_diff(commit_hash):
    """Gets the diff for a specific commit hash."""
    return run_git_command(["git", "show", commit_hash])


def call_gemini_for_diff_analysis(diff1, diff2):
    """Sends two diffs to the Gemini model for semantic comparison."""
    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        
        prompt = f"""
        You are an expert software engineer performing a code review. Your task is to determine if two git diffs are semantically and functionally equivalent.

        Ignore superficial differences such as:
        - Whitespace changes
        - Comments
        - Renaming of local variables if the logic is unaffected

        Focus on whether both code changes produce the exact same functional result.

        Here is Diff 1:
        ```diff
        {diff1}
        ```

        Here is Diff 2:
        ```diff
        {diff2}
        ```

        Are these two diffs semantically equivalent? Respond ONLY with a valid JSON object containing two keys: "is_equivalent" (a boolean) and "explanation" (a brief string explaining your reasoning).
        """
        
        response = model.generate_content(prompt)
        # Clean up the response to ensure it's valid JSON
        cleaned_response = response.text.strip().lstrip("```json").rstrip("```")
        
        result = json.loads(cleaned_response)
        return result.get("is_equivalent", False), result.get("explanation", "No explanation provided.")

    except Exception as e:
        return False, "API call failed."


def get_pr_commit_hash(pr_number, github_token, repo_name="kubernetes/kubernetes"):
    """
    Retrieves the merge commit SHA for a given GitHub pull request.
    Requires a personal access token with 'repo' scope.
    """
    try:
        g = Github(auth=Auth.Token(github_token))
        repo = g.get_repo(repo_name)
        pr = repo.get_pull(int(pr_number))
        return pr.merge_commit_sha
    except UnknownObjectException:
        print_warning(f"Warning: PR #{pr_number} not found in {repo_name}.")
        return None
    except GithubException as e:
        print_fail(f"Error with GitHub API for PR #{pr_number}: {e}")
        return None
    except Exception as e:
        print_fail(f"An unexpected error occurred while checking PR status: {e}")
        return None

def is_commit_in_tag(commit_hash, tag_name):
    """
    Checks if a commit is an ancestor of a given tag using 'git merge-base'.
    Returns True if the command succeeds (exit code 0), otherwise False.
    """
    command = ["git", "merge-base", "--is-ancestor", commit_hash, tag_name]
    try:
        # Use subprocess.run directly to get the exit code
        result = subprocess.run(
            command,
            check=False, # We want to handle the non-zero exit code ourselves
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        return result.returncode == 0
    except FileNotFoundError:
        print_fail("Error: 'git' command not found.")
        return False
    

def main():
    """Main function to run the git commit comparison."""

    print_header("--- Git LLM Reviewer Wizard ---")
    print("Please provide the required information for the review.")
    
    # Prompt for the target branch
    target_branch = questionary.text(
        "Enter the target branch name:",
        default="ocp/master"
    ).ask()

    # Get commits for the target branch to provide a list for the select menu
    target_commits_list = get_commits(target_branch, formatted=True, reverse=False)
    if not target_commits_list:
        print_warning(f"No commits found on branch '{target_branch}'. Cannot continue.")
        sys.exit(0)
    
    # Prompt for the target commit using fuzzy select
    target_commit_full = questionary.select(
        "Select the starting commit for the target branch:",
        choices=target_commits_list,
        style=select_style
    ).ask()
    target_commit = target_commit_full.split()[0] if target_commit_full else None
    
    # Prompt for the source branch and commit
    source_branch = questionary.text(
        "Enter the source branch name:",
        default="rebase-1.34"
    ).ask()

    # Get commits for the source branch to provide a list for the select menu
    source_commits_list = get_commits(source_branch, formatted=True, reverse=False)
    if not source_commits_list:
        print_warning(f"No commits found on branch '{source_branch}'. Cannot continue.")
        sys.exit(0)

    # Prompt for the source commit using fuzzy select
    source_commit_full = questionary.select(
        "Enter the starting commit hash for the source branch:",
        choices=source_commits_list,
        style=select_style
    ).ask()
    source_commit = source_commit_full.split()[0] if source_commit_full else None

    # Prompt for the Kubernetes tag
    k8s_tag = questionary.text(
        "Enter the Kubernetes tag to check against:",
        default="v1.34.1"
    ).ask()

    # Setup
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print_fail("Error: GEMINI_API_KEY environment variable not set.")
        sys.exit(1)
    genai.configure(api_key=api_key)

    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print_fail("Error: GITHUB_TOKEN environment variable not set. This is required for checking GitHub PRs.")
        sys.exit(1)

    print_header("\n--- Git LLM Reviewer Initialized ---")
    print(f"Comparing {colorize(target_branch, 'cyan')} (from {target_commit[:7]}) against {colorize(source_branch, 'cyan')} (from {source_commit[:7]})")
    
    # 1. Fetch commit data
    print("\nFetching commit data...")
    source_commits = get_commits(source_branch, source_commit)
    target_commits = get_commits(target_branch, target_commit)
    
    if not target_commits:
        print_warning(f"No new commits found on branch '{target_branch}' since '{target_commit[:7]}'. Exiting.")
        sys.exit(0)
        
    source_commit_map = {commit["message"]: commit["hash"] for commit in source_commits}
    print(f"Found {len(target_commits)} commits to check in '{target_branch}'.")

    # --- 2. Comparison Logic ---
    reporter = Reporter()
    pr_commit_pattern = re.compile(r"^UPSTREAM: (\d+):?.*")

    for commit_in_target_branch in target_commits:
        message = commit_in_target_branch["message"]
        commit_hash = commit_in_target_branch['hash']
        short_hash = commit_hash[:7]

        reporter.checking(commit_hash, message)

        pr_match = pr_commit_pattern.match(message)

        if pr_match:
            pr_number = pr_match.group(1)
            reporter.pr_found(pr_number, k8s_tag)

            pr_commit_hash = get_pr_commit_hash(pr_number, github_token)

            # Scenario 1: The PR's commit exists in the official K8s tag
            if pr_commit_hash and is_commit_in_tag(pr_commit_hash, k8s_tag):
                reporter.pr_in_tag(pr_number, k8s_tag)

                if message in source_commit_map:
                    reporter.failed(message, "Expected to be absent from source branch")
                else:
                    reporter.verified(message, "PR is in the tag and correctly absent from source branch")

            # Scenario 2: The PR's commit is NOT in the official K8s tag
            else:
                reporter.pr_not_in_tag(pr_number, k8s_tag)
                if message not in source_commit_map:
                    reporter.failed(message, f"Not found in {source_branch}")
                else:
                    commit_source_hash = source_commit_map[message]
                    reporter.analyzing_diffs()
                    diff1 = get_diff(commit_hash)
                    diff2 = get_diff(commit_source_hash)

                    is_equivalent, explanation = call_gemini_for_diff_analysis(diff1, diff2)

                    if is_equivalent:
                        reporter.verified(message, "Diffs are semantically equivalent")
                    else:
                        reporter.failed(message, f"Diff mismatch: {explanation}")

        elif message.startswith("UPSTREAM: <drop>"):
            reporter.skipped(message)

        elif message.startswith("UPSTREAM: <carry>"):
            if message not in source_commit_map:
                reporter.failed(message, f"Not found in {source_branch}")
            else:
                commit_source_hash = source_commit_map[message]
                reporter.analyzing_diffs()
                diff1 = get_diff(commit_hash)
                diff2 = get_diff(commit_source_hash)

                is_equivalent, explanation = call_gemini_for_diff_analysis(diff1, diff2)

                if is_equivalent:
                    reporter.verified(message, "Diffs are semantically equivalent")
                else:
                    reporter.failed(message, f"Diff mismatch: {explanation}")
        else:
            reporter.notice(message, "Non-standard commit found")

    # --- 4. Final Report ---
    has_failures = reporter.print_report()

    if has_failures:
        sys.exit(1)

if __name__ == "__main__":
    main()
