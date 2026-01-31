---
title: LLM App Deployer
emoji: 🚀
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
license: mit
---

# LLM App Deployer

AI-powered web application generator and deployer. Creates and updates GitHub repositories with generated HTML apps using AIPipe and OpenAI.

## Features

- 🤖 AI-powered code generation via AIPipe
- 📦 Automatic GitHub repository management
- 🌐 GitHub Pages deployment
- 🔄 Round-based updates (Create & Update)

## Configuration

Set these secrets in Hugging Face Space settings:

- `MY_SECRET`: Your authentication secret
- `GITHUB_TOKEN`: GitHub personal access token with `repo` scope
- `GITHUB_USERNAME`: Your GitHub username
- `AIPIPE_API_KEY`: Your AIPipe API key

## API Endpoints

### GET /

Health check endpoint

### POST /api/deploy

Deploy or update an application

**Request Body:**

```json
{
  "secret": "your-secret",
  "round": 1,
  "email": "your-email@example.com",
  "task": "app-name",
  "brief": "App description",
  "checks": [],
  "attachments": [],
  "evaluation_url": "https://your-callback-url.com",
  "nonce": "unique-id"
}
```

## Usage

Send POST request to `/api/deploy` with your app requirements. The service will:

1. Generate code using AI
2. Create/update GitHub repository
3. Enable GitHub Pages
4. Notify your callback URL

## 🚀 Deployment to Hugging Face Spaces

### Prerequisites

1. **Hugging Face Account**: Sign up at [huggingface.co](https://huggingface.co)
2. **GitHub Token**: Personal access token with `repo` scope
3. **AIPipe API Key**: Your AIPipe API key
4. **Git installed**: For pushing code

### Local Docker Testing (Optional)

Test your Docker build locally before deploying:

```bash
# Build Docker image
docker build -t llm-app-deployer:test .

# Run container with environment variables
docker run -p 7860:7860 \
  -e MY_SECRET="your-secret" \
  -e GITHUB_TOKEN="your-github-token" \
  -e GITHUB_USERNAME="your-username" \
  -e AIPIPE_API_KEY="your-aipipe-key" \
  llm-app-deployer:test
```

Or use the test script:

```bash
chmod +x test_docker.sh
./test_docker.sh
```

Access at: http://localhost:7860

### Updating Your Deployment

When you make changes to the code:

```bash
# Stage changes
git add .

# Commit
git commit -m "Update: description of changes"

# Push to Hugging Face
git push hf main
```

The Space will automatically rebuild and redeploy!

### Monitoring and Logs

**View Logs:**

1. Go to your Space page on Hugging Face
2. Click on **"Logs"** tab
3. Monitor real-time logs

**Check Space Status:**

- ✅ **Running**: Everything working
- 🔄 **Building**: Deploying changes
- ❌ **Runtime Error**: Check logs for details

### Troubleshooting

**Build Failed:**

- Verify `Dockerfile` and `.dockerignore` are committed
- Check all files are present: `main.py`, `requirements.txt`
- Review build logs in Space

**Runtime Errors:**

- Ensure all 4 secrets are added correctly
- Verify GitHub token has `repo` scope
- Check AIPIPE_API_KEY is valid
- View detailed logs in Space settings

**API Not Responding:**

- Wait 2-5 minutes after deployment completes
- Test health endpoint first
- Check Space status is "Running"

**GitHub API Errors:**

- Verify GitHub token permissions
- Check token hasn't expired
- Ensure repository creation is allowed

### Docker Configuration

The `Dockerfile` includes:

- ✅ Python 3.11 slim (optimized size)
- ✅ Git for PyGithub operations
- ✅ Non-root user (security best practice)
- ✅ Port 7860 (Hugging Face standard)
- ✅ Health checks
- ✅ Optimized layer caching

### Features After Deployment

Your deployed app will have:

- 🌐 Public HTTPS endpoint
- 🔒 Secure secret management
- 📊 Real-time logging
- 🔄 Auto-rebuild on git push
- ⚡ Fast API responses (<1s)
- 🛡️ Built-in security (non-root user)
- 📈 Persistent storage
- 🔍 Health monitoring

### API Usage Examples

**Round 1 - Create New App:**

```bash
curl -X POST https://YOUR_USERNAME-SPACE_NAME.hf.space/api/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "secret": "YOUR_SECRET",
    "round": 1,
    "email": "your-email@example.com",
    "task": "calculator",
    "brief": "Create a calculator with basic operations",
    "checks": [
      "Should have number buttons",
      "Should have operation buttons",
      "Should display results"
    ],
    "attachments": [],
    "evaluation_url": "https://your-callback.com/notify",
    "nonce": "unique-id-123"
  }'
```

**Round 2 - Update Existing App:**

```bash
curl -X POST https://YOUR_USERNAME-SPACE_NAME.hf.space/api/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "secret": "YOUR_SECRET",
    "round": 2,
    "email": "your-email@example.com",
    "task": "calculator",
    "brief": "Add memory functions and history",
    "checks": [
      "Should have memory buttons",
      "Should show calculation history"
    ],
    "attachments": [],
    "evaluation_url": "https://your-callback.com/notify",
    "nonce": "unique-id-456"
  }'
```

### Security Best Practices

1. ✅ **Never commit secrets** to git
2. ✅ Use Hugging Face secrets for all sensitive data
3. ✅ Rotate tokens periodically
4. ✅ Keep Space private if handling sensitive data
5. ✅ Monitor API usage and logs
6. ✅ Use strong authentication secrets

### Getting Help

**Documentation:**

- This README
- [Hugging Face Spaces Docs](https://huggingface.co/docs/hub/spaces)
- [Docker Documentation](https://docs.docker.com/)

**Support:**

- Hugging Face Community: [discuss.huggingface.co](https://discuss.huggingface.co)
- GitHub Issues: Report bugs in your repository
- Space Logs: Check for detailed error messages

## License

MIT License
