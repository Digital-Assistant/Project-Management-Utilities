import subprocess
import shutil
import sys
import pandas as pd
import tempfile
import re
from pathlib import Path


# --- PREREQUISITE AND VALIDATION FUNCTIONS ---

def check_gh_prerequisites():
    """Checks for gh installation and authentication."""
    print("1. Checking for GitHub CLI ('gh')...")
    if not shutil.which("gh"):
        print("\nERROR: GitHub CLI ('gh') is not installed or not in your PATH.")
        print("Please install it to continue: https://cli.github.com/")
        sys.exit(1)
    print("   'gh' is installed.")

    print("\n2. Checking GitHub authentication status...")
    try:
        subprocess.run(["gh", "auth", "status"], check=True, capture_output=True)
        print("   Successfully authenticated with GitHub.")
    except subprocess.CalledProcessError:
        print("\nERROR: You are not authenticated with the GitHub CLI.")
        print("Please run 'gh auth login' in your terminal to authenticate.")
        sys.exit(1)


def check_gh_scopes():
    """Checks if the authenticated gh token has the required scopes."""
    print("\n3. Checking for required permissions (scopes)...")
    # try:
    #     result = subprocess.run(["gh", "auth", "status", "-t"], check=True, capture_output=True, text=True)
    #     token_status = result.stdout
    #
    #     # Define all scopes required for creating issues, labels, and adding to organization projects.
    #     required_scopes = {'repo', 'project', 'read:org'}
    #     present_scopes = set()
    #
    #     # Robustly parse the "Token scopes" line from the command output.
    #     for line in token_status.splitlines():
    #         # The line looks like: "✓ Token scopes: project, read:org, repo"
    #         if 'token scopes:' in line.lower():
    #             scopes_part = line.split(':', 1)[1]
    #             present_scopes = {s.strip() for s in scopes_part.split(',')}
    #             break
    #
    #     missing_scopes = required_scopes - present_scopes
    #
    #     if not missing_scopes:
    #         print(f"   SUCCESS: Required scopes ({', '.join(sorted(list(required_scopes)))}) are present.")
    #     else:
    #         sorted_missing = sorted(list(missing_scopes))
    #         all_scopes_str = ' '.join([f"-s {s}" for s in sorted(list(required_scopes))])
    #         print(f"\nERROR: Your token is missing required scopes: {', '.join(sorted_missing)}")
    #         print("The script requires full permissions to create issues, labels, and add them to organization projects.")
    #         print(f"To fix this, please run: gh auth refresh -h github.com {all_scopes_str}")
    #         sys.exit(1)
    # except subprocess.CalledProcessError as e:
    #     print(f"\nERROR: Could not verify token scopes. Reason: {e.stderr.strip()}")
    #     sys.exit(1)


def get_and_validate_paths():
    """Gets input path from user and intelligently finds the state file."""
    while True:
        filepath_str = input("\n4. Please enter the path to your input CSV file: ")
        input_path = Path(filepath_str.strip())
        if input_path.exists() and input_path.is_file() and input_path.suffix.lower() == '.csv':
            print(f"   Input file found: {input_path}")
            break
        else:
            print("   ERROR: File not found or is not a .csv file. Please try again.")

    output_path = Path(f"{input_path.stem}_output.csv")
    state_path = None
    if output_path.exists():
        resume = input(f"   Found existing state file '{output_path}'. Resume from this file? (Y/n): ").lower().strip()
        if resume == '' or resume == 'y':
            state_path = output_path
            print(f"   Resuming run. Will use '{state_path}' to skip completed issues.")

    return input_path, state_path, output_path


def validate_dataframe(df):
    """Performs a pre-validation pass on the entire DataFrame."""
    print("\n5. Performing pre-upload validation of the CSV file...")
    errors = []
    required_columns = ['repository', 'title', 'parent_title', 'body', 'project_number']

    for col in required_columns:
        if col not in df.columns: errors.append(f"Missing required column: '{col}'")
    if errors: return errors

    titles = set(df['title'].tolist())
    for index, row in df.iterrows():
        if pd.isna(row['repository']) or not row['repository'].strip():
            errors.append(f"Row {index + 2}: 'repository' field cannot be empty.")
        if pd.isna(row['title']) or not row['title'].strip():
            errors.append(f"Row {index + 2}: 'title' field cannot be empty.")
        if pd.notna(row['parent_title']) and row['parent_title'].strip() and row['parent_title'] not in titles:
            errors.append(
                f"Row {index + 2}: 'parent_title' ('{row['parent_title']}') does not match any 'title' in the file.")

    if not errors:
        print("   Validation successful.")
    return errors


def create_missing_label(repo, error_message):
    """Parses a missing label from an error and creates it."""
    match = re.search(r"could not add label: '(.*?)' not found", error_message)
    if not match: return False, "Could not parse label name from error."

    missing_label = match.group(1)
    print(f"      -> WARNING: Label '{missing_label}' not found. Attempting to create it...")
    try:
        color = "%06x" % (hash(missing_label) & 0xFFFFFF)
        label_cmd = ["gh", "label", "create", missing_label, "--repo", repo, "--color", color]
        subprocess.run(label_cmd, check=True, capture_output=True, text=True)
        print(f"      -> SUCCESS: Label '{missing_label}' created.")
        return True, None
    except subprocess.CalledProcessError as e:
        return False, f"Failed to create missing label '{missing_label}'. Reason: {e.stderr.strip()}"


# --- CORE LOGIC ---

def process_issue(issue_data, issue_map):
    """Recursive function to process an issue and its children first."""
    # Base case: if issue is already processed, return its URL
    # Convert to string to prevent errors if pandas reads an empty cell as NaN (float).
    # This handles valid URLs, empty strings, and NaN values safely.
    if str(issue_data.get('github_issue_url', '')).startswith('https'):
        return issue_data['github_issue_url']

    # Recursive step: process all children first
    children_titles = issue_data.get('children', [])
    child_issue_map = {title: issue_map[title] for title in children_titles}

    for title, child_data in child_issue_map.items():
        process_issue(child_data, issue_map)

    # Now, process the current issue
    print(f"\nProcessing: '{issue_data['title']}'")

    repo = issue_data.get('repository')
    body_with_links = issue_data.get('body')

    # If it's a parent, construct the final body with child links
    if children_titles:
        links = []
        for title in children_titles:
            child_url = issue_map[title].get('github_issue_url', '')
            if child_url.startswith('https'):
                issue_number = f"#{child_url.split('/')[-1]}"
                links.append(f"- [ ] {issue_number} {title}")
            else:
                links.append(f"- [ ] (Failed) {title}")

        body_with_links += "\n\n### Child Issues\n" + "\n".join(links)

    # --- Create the issue (with retries for missing labels) ---
    issue_url = None
    for attempt in range(5):
        cmd = ["gh", "issue", "create", "--repo", repo]
        cmd.extend(["--title", issue_data.get('title')])

        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".md") as tf:
            tf.write(body_with_links)
            body_filepath = tf.name
        cmd.extend(["--body-file", body_filepath])

        if pd.notna(issue_data.get('labels')): cmd.extend(["--label", issue_data.get('labels')])
        if pd.notna(issue_data.get('assignees')): cmd.extend(["--assignee", issue_data.get('assignees')])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            issue_url = result.stdout.strip()
            issue_data['github_issue_url'] = issue_url
            print(f"   -> SUCCESS (Step 1/2): Created issue -> {issue_url}")
            break
        except subprocess.CalledProcessError as e:
            error_message = e.stderr.strip()
            if "could not add label" in error_message and "not found" in error_message:
                success, remediation_error = create_missing_label(repo, error_message)
                if not success:
                    issue_data['github_issue_url'] = f"ERR: {remediation_error}"
                    break
            else:
                issue_data['github_issue_url'] = f"ERR: {error_message}"
                break
        finally:
            Path(body_filepath).unlink()

    if not issue_url:
        return None

    # --- Add to project ---
    try:
        owner = repo.split('/')[0]
        project_num = str(issue_data.get('project_number'))
        print(f"   -> Attempting (Step 2/2): Add to Org Project '{owner}' Number '{project_num}'")
        project_cmd = ["gh", "project", "item-add", project_num, "--owner", owner, "--url", issue_url]
        subprocess.run(project_cmd, check=True, capture_output=True, text=True)
        print(f"   -> SUCCESS (Step 2/2): Added to project.")
    except subprocess.CalledProcessError as e:
        error_message = f"ERR: Issue created but FAILED to add to project. Reason: {e.stderr.strip()}"
        issue_data['github_issue_url'] = error_message
        print(f"   -> FAILURE (Step 2/2): {error_message}")

    return issue_url


def main():
    """Main script execution."""
    check_gh_prerequisites()
    check_gh_scopes()
    input_path, state_path, output_path = get_and_validate_paths()

    try:
        df = pd.read_csv(input_path, converters={'project_number': str})
    except Exception as e:
        print(f"\nERROR: Could not read CSV file. Reason: {e}")
        sys.exit(1)

    validation_errors = validate_dataframe(df)
    if validation_errors:
        print("\nValidation failed. Please fix these issues and try again:")
        for error in validation_errors: print(f"- {error}")
        sys.exit(1)

    # --- Phase 1: Build the Tree & Merge State ---
    issue_map = {row['title']: row.to_dict() for index, row in df.iterrows()}
    roots = []

    if state_path:
        print(f"\n6. Merging state from '{state_path}'...")
        state_df = pd.read_csv(state_path)
        for index, row in state_df.iterrows():
            if row['title'] in issue_map:
                issue_map[row['title']]['github_issue_url'] = row['github_issue_url']
        print("   State merged successfully.")

    for title, data in issue_map.items():
        parent_title = data.get('parent_title')
        if pd.notna(parent_title) and parent_title in issue_map:
            if 'children' not in issue_map[parent_title]:
                issue_map[parent_title]['children'] = []
            issue_map[parent_title]['children'].append(title)
        else:
            roots.append(data)

    print("\n7. Starting hierarchical issue creation process...")

    # --- Phase 2: Process the Tree ---
    for root_data in roots:
        process_issue(root_data, issue_map)
        # Save progress after each top-level root is processed
        pd.DataFrame.from_dict(issue_map, orient='index').to_csv(output_path, index=False)

    print(f"\nProcess complete. Final results saved to '{output_path}'.")


if __name__ == "__main__":
    main()