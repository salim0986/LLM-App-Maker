from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv
import json
import requests
from github import Github
import base64
import time
from threading import Thread


load_dotenv()

app = FastAPI()

# Constants
INDEX_HTML = "index.html"
README_MD = "README.md"

# Load secrets
MY_SECRET = os.getenv("MY_SECRET")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
AIPIPE_API_KEY = os.getenv("AIPIPE_API_KEY")

# Initialize GitHub client
try:
    github_client = Github(GITHUB_TOKEN)
    print("✅ GitHub client initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize GitHub client: {e}")
    github_client = None

@app.get("/")
def home():
    return {
        "status": "LLM App Deployer is running!", 
        "using": "AIPipe API",
        "supported_rounds": [1, 2],
        "round_1": "Creates new repository with app",
        "round_2": "Updates existing repository with new features"
    }



# -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
def call_aipipe_api(input_text, model="gpt-4o-mini", max_retries=3, use_openai_api=True):
    """
    Calls AIPipe API with retry logic
    Can use either OpenAI API format or OpenRouter API format
    """
    if not AIPIPE_API_KEY:
        raise RuntimeError("AIPIPE_API_KEY not found in environment variables")
    
    headers = {
        "Authorization": f"Bearer {AIPIPE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    if use_openai_api:
        # OpenAI API format - simpler for responses
        url = "https://aipipe.org/openai/v1/responses"
        payload = {
            "model": model,
            "input": input_text
        }
    else:
        # OpenRouter API format - for chat completions
        url = "https://aipipe.org/openrouter/v1/chat/completions"
        payload = {
            "model": f"openai/{model}",
            "messages": [{"role": "user", "content": input_text}]
        }
    
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=120)
            
            if response.status_code == 200:
                result = response.json()
                
                # Parse based on API format
                if use_openai_api:
                    # OpenAI responses format: {"output": [{"content": [{"text": "..."}]}]}
                    if 'output' in result and len(result['output']) > 0:
                        output_item = result['output'][0]
                        if 'content' in output_item and len(output_item['content']) > 0:
                            return output_item['content'][0].get('text', '')
                else:
                    # OpenRouter format: {"choices": [{"message": {"content": "..."}}]}
                    if 'choices' in result and len(result['choices']) > 0:
                        return result['choices'][0]['message']['content']
                
                # Fallback: try to find any text content
                print(f"⚠️  Unexpected response structure: {list(result.keys())}")
                return str(result)
                
            else:
                print(f"⚠️  AIPipe API returned {response.status_code}: {response.text[:200]}")
                
        except Exception as e:
            print(f"⚠️  Attempt {attempt + 1} failed: {e}")
            
        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)  # Exponential backoff
    
    raise RuntimeError(f"Failed to get response from AIPipe after {max_retries} attempts")
# -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
def generate_app_code(brief, attachments, checks):
    """
    Uses AI (via AIPipe) to generate the app code
    """
    
    # Prepare attachments info for AI
    attachment_info = ""
    if attachments:
        attachment_info = "\n\nATTACHMENTS PROVIDED:"
        for att in attachments:
            attachment_info += f"\n- {att['name']}: {att['url']}"
    
    # Prepare checks info for AI
    checks_info = ""
    if checks:
        checks_info = "\n\nCRITICAL - THESE JAVASCRIPT CHECKS MUST PASS:"
        for check in checks:
            checks_info += f"\n- {check}"
    
    # Create prompt for AI
    prompt = f"""You are an expert web developer. Create a single, complete HTML file for a web application.

BRIEF:
{brief}
{attachment_info}
{checks_info}

CRITICAL REQUIREMENTS:
1. Create a SINGLE, COMPLETE HTML file with ALL code inline
2. Include ALL JavaScript inline within <script> tags (no external JS files)
3. Include ALL CSS inline within <style> tags (no external CSS files except CDN libraries)
4. You MUST implement EVERY element ID, class, and functionality mentioned in the checks
5. If checks mention specific element IDs (like #total-sales, #markdown-output), you MUST create those exact elements
6. If checks mention loading libraries (Bootstrap, marked.js, highlight.js), you MUST include them via CDN
7. Handle data from attachments by fetching from their URLs (they are data: URLs)
8. Make the app functional, responsive, and professional
9. Add clear comments explaining the code
10. Ensure ALL JavaScript checks will pass when executed

IMPORTANT: The checks are JavaScript expressions that will be run on your page. Make sure your HTML structure and JavaScript logic satisfy ALL of them.

OUTPUT FORMAT:
Return ONLY the complete HTML code. Do not include any explanations, markdown formatting, or code fences. Start with <!DOCTYPE html>."""

    # Call AIPipe API using OpenAI responses endpoint with gpt-4o for best quality
    code = call_aipipe_api(prompt, model="gpt-4o", use_openai_api=True)
    
    # Clean up (remove markdown code fences if present)
    if "```html" in code:
        code = code.split("```html")[1].split("```")[0]
    elif "```" in code:
        code = code.split("```")[1].split("```")[0]
    
    return code.strip()
# -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def generate_readme(brief, repo_name, is_update=False):
    """
    Uses AI (via AIPipe) to generate a professional README
    """
    if is_update:
        prompt = f"""Update the README.md for this GitHub repository with new features.

PROJECT: {repo_name}
NEW FEATURES/UPDATES: {brief}

Create a comprehensive README that includes:
1. Project Title and Description (updated)
2. Features (include new features)
3. Recent Updates section
4. Setup Instructions
5. Usage (updated if needed)
6. Code Explanation (brief)
7. License (MIT)

Make it clear that this is an updated version with new capabilities."""
    else:
        prompt = f"""Create a professional README.md for this GitHub repository.

PROJECT: {repo_name}
DESCRIPTION: {brief}

Include these sections:
1. Project Title and Description
2. Features
3. Setup Instructions
4. Usage
5. Code Explanation (brief)
6. License (MIT)

Make it clear, professional, and helpful."""

    # Use AIPipe OpenAI API for README generation with correct model
    readme_content = call_aipipe_api(prompt, model="gpt-4o-mini", use_openai_api=True)
    return readme_content.strip()

# -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
def ensure_pages_on_main_branch(repo):
    """
    Ensures GitHub Pages is configured to deploy from main branch
    """
    try:
        import requests
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        # Get current Pages configuration
        pages_url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo.name}/pages"
        response = requests.get(pages_url, headers=headers)
        
        if response.status_code == 200:
            pages_info = response.json()
            current_branch = pages_info.get('source', {}).get('branch', '')
            
            if current_branch != 'main':
                # Update to main branch
                print(f"⚠️ Pages currently on '{current_branch}' branch, updating to 'main'...")
                update_data = {
                    "source": {
                        "branch": "main",
                        "path": "/"
                    }
                }
                update_response = requests.put(pages_url, headers=headers, json=update_data)
                
                if update_response.status_code in [200, 204]:
                    print("✅ GitHub Pages updated to main branch")
                    return True
                else:
                    print(f"⚠️ Failed to update Pages branch: {update_response.status_code}")
                    print(f"Response: {update_response.text}")
            else:
                print("✅ GitHub Pages already on main branch")
                return True
        elif response.status_code == 404:
            # Pages not enabled yet
            print("ℹ️ GitHub Pages not yet enabled, will create...")
            return False
        else:
            print(f"⚠️ Could not check Pages configuration: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"⚠️ Error checking Pages configuration: {e}")
        return False

# -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
def generate_unique_repo_name(task_id, base_suffix="-round1", max_attempts=10):
    """
    Generate a unique repository name that doesn't conflict with existing repos
    """
    import re
    user = github_client.get_user()
    
    # Sanitize task_id: replace spaces and special chars with hyphens
    sanitized_task_id = re.sub(r'[^a-zA-Z0-9-]', '-', task_id)
    # Remove consecutive hyphens
    sanitized_task_id = re.sub(r'-+', '-', sanitized_task_id)
    # Remove leading/trailing hyphens
    sanitized_task_id = sanitized_task_id.strip('-').lower()
    
    # Try the base name first
    base_name = f"{sanitized_task_id}{base_suffix}"
    
    # Check if base name is available
    try:
        user.get_repo(base_name)
        # Repo exists, need to generate unique name
        print(f"⚠️ Repository '{base_name}' already exists, generating unique name...")
    except:
        # Repo doesn't exist, we can use the base name
        return base_name
    
    # Try with timestamp
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    timestamped_name = f"{sanitized_task_id}{base_suffix}-{timestamp}"
    
    try:
        user.get_repo(timestamped_name)
        # Still exists (very unlikely), try with counter
        print(f"⚠️ Repository '{timestamped_name}' also exists, trying with counter...")
    except:
        print(f"✅ Using unique name: {timestamped_name}")
        return timestamped_name
    
    # Last resort: try with counter
    for i in range(1, max_attempts + 1):
        counter_name = f"{task_id}{base_suffix}-v{i}"
        try:
            user.get_repo(counter_name)
            continue  # Exists, try next
        except:
            print(f"✅ Using unique name: {counter_name}")
            return counter_name
    
    # If all attempts fail, use timestamp + random suffix
    import random
    random_suffix = random.randint(1000, 9999)
    final_name = f"{task_id}{base_suffix}-{timestamp}-{random_suffix}"
    print(f"✅ Using unique name with random suffix: {final_name}")
    return final_name

# -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
def create_github_repo(task_id, app_code, readme_content):
    """
    Creates a new GitHub repository with the app (Round 1 only)
    """
    # Generate unique repo name (handles conflicts)
    repo_name = generate_unique_repo_name(task_id, "-round1")
    
    try:
        # Create repository
        user = github_client.get_user()
        print(f"📦 Creating repository: {repo_name}")
        repo = user.create_repo(
            repo_name,
            description=f"Auto-generated app for {task_id}",
            private=False,
            auto_init=False
        )
        
        # Add MIT License
        license_content = """MIT License

Copyright (c) 2025

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""
        
        repo.create_file(
            "LICENSE",
            "Add MIT License",
            license_content
        )
        
        # Add README
        repo.create_file(
            README_MD,
            "Add README",
            readme_content
        )
        
                # Add index.html (the app)
        repo.create_file(
            INDEX_HTML,
            "Add main application",
            app_code
        )
        
        # Enable GitHub Pages on main branch
        print("📄 Configuring GitHub Pages...")
        
        # Wait a moment for repo to be ready
        time.sleep(2)
        
        # Check if Pages is already configured
        pages_exists = ensure_pages_on_main_branch(repo)
        
        if not pages_exists:
            # Pages not enabled yet, create it
            # Use direct API method since PyGithub doesn't have create_pages_site
            try:
                import requests
                headers = {
                    "Authorization": f"token {GITHUB_TOKEN}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28"
                }
                pages_url_api = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo.name}/pages"
                pages_data = {
                    "source": {
                        "branch": "main",
                        "path": "/"
                    }
                }
                
                print(f"📡 Enabling GitHub Pages via API...")
                response = requests.post(pages_url_api, headers=headers, json=pages_data)
                
                if response.status_code == 201:
                    print("✅ GitHub Pages enabled on main branch")
                    time.sleep(2)
                    ensure_pages_on_main_branch(repo)
                elif response.status_code == 409:
                    print("ℹ️ GitHub Pages already exists, verifying configuration...")
                    ensure_pages_on_main_branch(repo)
                else:
                    print(f"⚠️ GitHub Pages API response: {response.status_code}")
                    print(f"Response: {response.text}")
                    # Continue anyway - Pages might still work
                    
            except Exception as pages_error:
                print(f"⚠️ GitHub Pages setup error: {pages_error}")
                # Continue anyway - repository is created
        
        # Get commit SHA
        commits = repo.get_commits()
        latest_commit_sha = commits[0].sha
        
        # Construct URLs
        repo_url = repo.html_url
        pages_url = f"https://{GITHUB_USERNAME}.github.io/{repo_name}/"
        
        # Wait for GitHub Pages to deploy and return 200 OK
        print("⏳ Waiting for GitHub Pages to deploy...")
        max_attempts = 30
        pages_ready = False
        
        for attempt in range(max_attempts):
            time.sleep(10)  # Wait 10 seconds between checks
            try:
                print(f"   Checking Pages deployment (attempt {attempt + 1}/{max_attempts})...")
                response = requests.get(pages_url, timeout=10, allow_redirects=True)
                
                if response.status_code == 200:
                    print(f"✅ GitHub Pages is live and returning 200 OK!")
                    print(f"   URL: {pages_url}")
                    pages_ready = True
                    break
                else:
                    print(f"   Status: {response.status_code}, retrying...")
                    
            except requests.exceptions.RequestException as e:
                print(f"   Connection error: {str(e)[:50]}, retrying...")
                
        if not pages_ready:
            print(f"⚠️ Warning: GitHub Pages did not return 200 OK after {max_attempts * 10} seconds")
            print(f"   But repository and Pages are configured. It may take more time to deploy.")
        
        return {
            "repo_url": repo_url,
            "commit_sha": latest_commit_sha,
            "pages_url": pages_url,
            "repo_name": repo_name,
            "pages_ready": pages_ready
        }
        
    except Exception as e:
        print(f"Error creating repo: {e}")
        raise

# -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
def find_round1_repo(task_id):
    """
    Find the Round 1 repository for a given task_id
    Handles cases where repo might have timestamp/counter suffixes due to naming conflicts
    Always returns the MOST RECENTLY CREATED repository if multiple matches exist
    """
    import re
    user = github_client.get_user()
    
    # Sanitize task_id the same way as in generate_unique_repo_name
    sanitized_task_id = re.sub(r'[^a-zA-Z0-9-]', '-', task_id)
    sanitized_task_id = re.sub(r'-+', '-', sanitized_task_id)
    sanitized_task_id = sanitized_task_id.strip('-').lower()
    
    # Search through ALL user's repos for matching pattern
    # Don't return early - we need to check all matches to find the newest
    print(f"🔍 Searching for {sanitized_task_id}-round1* repositories...")
    
    try:
        repos = user.get_repos()
        matching_repos = []
        
        for repo in repos:
            # Check if repo name matches pattern: sanitized_task_id-round1 with optional suffix
            if repo.name.startswith(f"{sanitized_task_id}-round1"):
                matching_repos.append(repo)
                print(f"   Found: {repo.name} (created: {repo.created_at})")
        
        if not matching_repos:
            raise Exception(f"No repository found matching pattern '{sanitized_task_id}-round1*'. Please create a Round 1 repository first.")
        
        # Sort by creation date - newest first
        matching_repos.sort(key=lambda r: r.created_at, reverse=True)
        
        # Use the most recent one
        selected_repo = matching_repos[0]
        
        if len(matching_repos) > 1:
            print(f"⚠️ Found {len(matching_repos)} matching repositories")
            print(f"✅ Using MOST RECENT: {selected_repo.name} (created: {selected_repo.created_at})")
        else:
            print(f"✅ Found repository: {selected_repo.name}")
        
        return selected_repo
        
    except Exception as e:
        raise Exception(f"Error finding Round 1 repository: {e}")

# -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
def update_github_repo(task_id, app_code, readme_content, brief):
    """
    Updates existing GitHub repository with new features (Round 2)
    """
    try:
        # Find the Round 1 repository (handles naming conflicts)
        repo = find_round1_repo(task_id)
        repo_name = repo.name
        
        # Update index.html
        try:
            file = repo.get_contents(INDEX_HTML)
            repo.update_file(
                INDEX_HTML,
                f"Round 2 update: {brief}",
                app_code,
                file.sha
            )
            print("✅ Updated index.html")
        except Exception as e:
            print(f"Error updating index.html: {e}")
            raise
        
        # Update README.md
        try:
            file = repo.get_contents(README_MD)
            repo.update_file(
                README_MD,
                "Round 2 update: Updated README",
                readme_content,
                file.sha
            )
            print("✅ Updated README.md")
        except Exception as e:
            print(f"Error updating README.md: {e}")
            raise
        
        # Ensure GitHub Pages is still on main branch
        print("📄 Verifying GitHub Pages configuration...")
        ensure_pages_on_main_branch(repo)
        
        # Wait a moment for changes to propagate
        time.sleep(2)
        
        # Get latest commit SHA
        commits = repo.get_commits()
        latest_commit_sha = commits[0].sha
        
        # Construct URLs
        repo_url = repo.html_url
        pages_url = f"https://{GITHUB_USERNAME}.github.io/{repo_name}/"
        
        # Wait for GitHub Pages to update and return 200 OK
        print("⏳ Waiting for GitHub Pages to update...")
        max_attempts = 30
        pages_ready = False
        
        for attempt in range(max_attempts):
            time.sleep(10)  # Wait 10 seconds between checks
            try:
                print(f"   Checking Pages update (attempt {attempt + 1}/{max_attempts})...")
                response = requests.get(pages_url, timeout=10, allow_redirects=True)
                
                if response.status_code == 200:
                    print(f"✅ GitHub Pages is live and returning 200 OK!")
                    print(f"   URL: {pages_url}")
                    pages_ready = True
                    break
                else:
                    print(f"   Status: {response.status_code}, retrying...")
                    
            except requests.exceptions.RequestException as e:
                print(f"   Connection error: {str(e)[:50]}, retrying...")
                
        if not pages_ready:
            print(f"⚠️ Warning: GitHub Pages did not return 200 OK after {max_attempts * 10} seconds")
            print(f"   But repository is updated. It may take more time to redeploy.")
        
        return {
            "repo_url": repo_url,
            "commit_sha": latest_commit_sha,
            "pages_url": pages_url,
            "repo_name": repo_name,
            "pages_ready": pages_ready
        }
        
    except Exception as e:
        print(f"Error updating repo: {e}")
        raise
# -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
def notify_evaluation_api(evaluation_url, email, task, round_num, nonce, repo_info):
    """
    Sends repo details to the evaluation API
    """
    payload = {
        "email": email,
        "task": task,
        "round": round_num,
        "nonce": nonce,
        "repo_url": repo_info["repo_url"],
        "commit_sha": repo_info["commit_sha"],
        "pages_url": repo_info["pages_url"]
    }
    
    max_retries = 5
    delay = 1
    
    for attempt in range(max_retries):
        try:
            response = requests.post(
                evaluation_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                print("✅ Successfully notified evaluation API")
                return True
            else:
                print(f"⚠️  Evaluation API returned {response.status_code}")
                
        except Exception as e:
            print(f"❌ Attempt {attempt + 1} failed: {e}")
        
        if attempt < max_retries - 1:
            time.sleep(delay)
            delay *= 2
    
    return False
# -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
def process_request_background(data):
    """
    Processes the request in the background
    """
    try:
        email = data["email"]
        task = data["task"]
        round_num = data["round"]
        nonce = data["nonce"]
        brief = data["brief"]
        checks = data["checks"]
        evaluation_url = data["evaluation_url"]
        attachments = data["attachments"]
        
        print(f"🚀 Processing task: {task} (Round {round_num})")
        
        # Step 1: Generate app code
        print("🤖 Generating app code with AI...")
        app_code = generate_app_code(brief, attachments, checks)
        
        # Step 2: Generate README
        print("📝 Generating README...")
        is_update = round_num == 2
        readme = generate_readme(brief, task, is_update)
        
        # Step 3: Handle repository based on round
        if round_num == 1:
            # Round 1: Create new repository
            print("📦 Creating new GitHub repository...")
            repo_info = create_github_repo(task, app_code, readme)
            wait_time = 30  # Longer wait for new repo and Pages setup
        elif round_num == 2:
            # Round 2: Update existing repository
            print("🔄 Updating existing GitHub repository...")
            repo_info = update_github_repo(task, app_code, readme, brief)
            wait_time = 15  # Shorter wait for updates
        else:
            raise ValueError(f"Unsupported round number: {round_num}")
        
        # Step 4: Wait for Pages to deploy/redeploy
        print("⏳ Waiting for GitHub Pages to deploy...")
        time.sleep(wait_time)
        
        # Step 5: Notify evaluation API
        print("📡 Notifying evaluation API...")
        notify_evaluation_api(evaluation_url, email, task, round_num, nonce, repo_info)
        
        print(f"✅ Task {task} (Round {round_num}) completed successfully!")
        print(f"🌐 App URL: {repo_info['pages_url']}")
        
    except Exception as e:
        print(f"❌ Error processing request: {e}")
# -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
@app.post("/api/deploy")
async def deploy_app(request: Request):
    """
    Main endpoint - receives request and processes in background
    """
    try:
        data = await request.json()
        
        # Verify secret
        if data.get("secret") != MY_SECRET:
            raise HTTPException(status_code=403, detail="Invalid secret")
        
        # Start background processing
        thread = Thread(target=process_request_background, args=(data,))
        thread.start()
        
        # Return immediate 200 OK
        return JSONResponse(
            status_code=200,
            content={"message": "Request received and processing"}
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )