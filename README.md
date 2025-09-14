# Project-Management-Utilities
Some general purpose utilities which need a home

# GitHub Issues Bulk Uploader (Hierarchical)

This directory contains a Python script (`issues_csv_to_github.py`) designed to bulk-create issues in a GitHub repository from a local CSV file. It intelligently handles hierarchical relationships (Epics -> Stories -> Tasks), creating issues from the bottom up and automatically linking parents to their children in the issue body.

The script is designed to be robust, providing pre-upload validation, resumability, and detailed feedback.

## Features

-   **Cross-Platform:** Runs on any system with Python and the GitHub CLI installed.
-   **Hierarchical Linking:** Creates parent issues (Epics, Stories) with Markdown checklists that link to their newly created children, enabling progress bars in the GitHub UI.
-   **Resumability:** Can detect a previous `_output.csv` file to resume an interrupted run, preventing duplicate issues.
-   **Self-Healing Labels:** Automatically creates missing labels in the target repository if they don't exist.
-   **Org-Level Project Support:** Correctly adds newly created issues to organization-level GitHub Projects (V2).
-   **Pre-Upload Validation:** Scans the entire CSV for format errors before making any API calls.
-   **Detailed Feedback:** Creates a new output CSV file (`*_output.csv`) populated with the URL of each successfully created issue or a specific error message.

## Prerequisites

Before using this script, you must have the following installed on your system:

1.  **Python 3:** The script is written in Python 3.
2.  **GitHub CLI (`gh`):** The underlying tool used to interact with the GitHub API.

## Setup Instructions

1.  **Clone the Repository:**
    ```bash
    git clone <your-repo-url>
    cd <your-repo-directory>
    ```

2.  **Create and Activate a Virtual Environment:**
    It is highly recommended to use a virtual environment to manage project-specific dependencies and avoid conflicts.

    First, ensure the `venv` module is available. The command may vary based on your operating system and Python version. For Debian/Ubuntu-based systems, you can run:
    ```bash
    # Make sure venv is available (example for Python 3.12)
    sudo apt install python3.12-venv -y
    ```

    Next, create the virtual environment within your project directory:
    ```bash
    # Create a venv inside your project
    python3 -m venv .venv
    ```

    Finally, activate the virtual environment. Your terminal prompt should change to indicate it's active.
    ```bash
    # Activate it
    source .venv/bin/activate
    ```

3.  **Install Python Dependencies:**
    With the virtual environment activated, upgrade `pip` and then install the required packages listed in `requirements.txt`.
    ```bash
    # Upgrade pip inside the venv
    pip install --upgrade pip

    # Install dependencies
    pip install -r requirements.txt
    ```

4.  **Install & Authenticate GitHub CLI:**
    If you don't have `gh` installed, follow the official instructions for your OS. Once installed, you must authenticate it with a token that has the correct permissions.

    Run the following command. It will open a web browser to guide you through the process.
    ```bash
    gh auth login
    ```
    When prompted for scopes, ensure you grant access to **`repo`** and **`project`** to allow the script to create issues, labels, and add items to projects. If you have already logged in, you can refresh your token with the correct scopes by running:
    ```bash
    gh auth refresh -h github.com -s repo -s project
    ```

## CSV File Format

The script is driven by a CSV file that defines the issue hierarchy. The file **must** contain the following columns.

### Column Schema

| Column | Required? | Description | Example |
| :--- | :--- | :--- | :--- |
| `repository` | **Yes** | The full name of the target repository. | `Digital-Assistant/Digital-Assistant-Server` |
| `title` | **Yes** | The title of the GitHub issue. Must be unique within the file. | `[Story] Establish Project Structure & Conventions` |
| `parent_title` | **Yes** | The exact title of the parent issue. Leave blank for top-level issues (Epics). | `[Epic] Foundational Infrastructure...` |
| `body` | **Yes** | The full markdown content for the issue's description. | `### Objective\nTo create a...` |
| `labels` | No | A comma-separated string of labels to apply. | `story,documentation` |
| `assignees` | No | A comma-separated string of GitHub usernames. | `your-github-username` |
| `project_name`| No | The human-readable name of the project (for clarity in the CSV). Ignored by the script. | `Moving from lexical search to Semantic Search` |
| `project_number`| **Yes**| The number of the organization-level GitHub Project (V2). | `6` |
| `github_issue_url`| No | Leave this column empty. The script will populate it with the results of the run. | |

### Sample CSV Data

```csv
"repository","title","parent_title","body","labels","assignees","project_name","project_number","github_issue_url"
"Digital-Assistant/Digital-Assistant-Server","[Epic] Foundational Infrastructure, Environment, & Conventions","","## Overview...",epic,"","Moving from lexical search to Semantic Search",6,
"Digital-Assistant/Digital-Assistant-Server","[Story] Establish Project Structure & Conventions","[Epic] Foundational Infrastructure, Environment, & Conventions","### User Story...",story,documentation,"","Moving from lexical search to Semantic Search",6,
"Digital-Assistant/Digital-Assistant-Server","Task: Create CONVENTIONS.md document","[Story] Establish Project Structure & Conventions","### Objective...",task,documentation,"","Moving from lexical search to Semantic Search",6,
```

## Usage Guide

1.  **Prepare your CSV file** according to the format specified above.
2.  **Activate the virtual environment** if it is not already active. You can verify this if your terminal prompt is prefixed with `(.venv)`. If not, run:
    ```bash
    source .venv/bin/activate
    ```
3.  **Run the script** from your terminal:
    ```bash
    python upload_issues_hierarchical.py
    ```
4.  **Follow the prompts:**
    *   The script will first validate your environment.
    *   It will then ask for the path to your input CSV file.
    *   It will automatically check for a corresponding `_output.csv` file and ask if you want to resume.
5.  **Check the Results:** After the script finishes, a new file named `[your_input_file]_output.csv` will be created. This file serves as a complete log of the operation, containing either the URL of the created issue or a specific error message in the `github_issue_url` column.
