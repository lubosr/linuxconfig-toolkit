# Git Setup Guide

## Initial Git Setup

After extracting the toolkit, initialize git:

```bash
cd linuxconfig-toolkit

# Initialize git repository
git init

# Add all files (credentials will be ignored automatically)
git add .

# First commit
git commit -m "Initial commit: LinuxConfig SEO Toolkit"

# Add remote (replace with your repo URL)
git remote add origin https://github.com/yourusername/linuxconfig-toolkit.git

# Push to remote
git branch -M main
git push -u origin main
```

## What Gets Committed

✅ **Committed to Git:**
- All Python scripts
- Docker configuration
- Database schema (init.sql)
- Documentation
- Shared libraries
- .gitkeep files (preserve directory structure)

❌ **NOT Committed (Protected by .gitignore):**
- API credentials (*.json, token.json)
- Database data (data/databases/*)
- CSV reports (data/reports/*.csv)
- SQL backups (*.sql)
- Python cache (__pycache__/)
- Environment files (.env)
- IDE files (.vscode/, .idea/)
- OS files (.DS_Store, Thumbs.db)
- Log files (*.log)

## Verify Before Push

Check what will be committed:

```bash
# See what's staged
git status

# Verify credentials are ignored
ls -la shared/config/credentials/
git check-ignore shared/config/credentials/*.json
# Should output: shared/config/credentials/*.json

# Check for accidental credential files
git ls-files | grep -E '\.(json|key|pem|env)$'
# Should be empty or show only non-sensitive files
```

## Adding Credentials After Clone

When someone clones the repo:

```bash
# Clone the repo
git clone https://github.com/yourusername/linuxconfig-toolkit.git
cd linuxconfig-toolkit

# Create credentials directory (exists but empty)
ls shared/config/credentials/  # Shows .gitkeep only

# Add your credentials
cp /path/to/linuxconfig-org-ed3c209ed133.json shared/config/credentials/
cp /path/to/token.json shared/config/credentials/

# Verify they're ignored
git status
# Should NOT show credential files
```

## Update .gitignore

To add more exclusions:

```bash
# Edit .gitignore
nano .gitignore

# Test what gets ignored
git check-ignore -v data/reports/test.csv

# Commit changes
git add .gitignore
git commit -m "Update .gitignore"
```

## Clean Working Directory

Remove untracked files (be careful!):

```bash
# See what would be deleted
git clean -n -d

# Remove untracked files and directories
git clean -f -d

# Remove ignored files too (credentials, data)
git clean -f -d -x
```

## Branch Strategy (Recommended)

```bash
# Create development branch
git checkout -b develop

# Make changes
git add .
git commit -m "Add new feature"

# Push to develop
git push origin develop

# Merge to main when ready
git checkout main
git merge develop
git push origin main
```

## Safety Checks

### Pre-commit Hook (Optional)

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Prevent committing credentials

if git diff --cached --name-only | grep -qE '\.(json|key|pem|env)$'; then
    echo "ERROR: Attempting to commit credential files!"
    echo "Files:"
    git diff --cached --name-only | grep -E '\.(json|key|pem|env)$'
    exit 1
fi

exit 0
```

Make executable:
```bash
chmod +x .git/hooks/pre-commit
```

### Scan for Secrets

```bash
# Check if credentials accidentally committed
git log -p | grep -i "password\|secret\|key" | head -20

# Search current files
grep -r "password" . --exclude-dir=.git --exclude-dir=data
```

## Troubleshooting

### Accidentally Committed Credentials

```bash
# Remove from history (DANGER - rewrites history)
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch shared/config/credentials/*.json" \
  --prune-empty --tag-name-filter cat -- --all

# Force push (if remote exists)
git push origin --force --all

# Regenerate compromised credentials immediately!
```

### File Still Showing in Git Status

```bash
# Remove from git tracking but keep file
git rm --cached path/to/file

# Commit the removal
git commit -m "Remove tracked file"
```

## Best Practices

1. **Never commit credentials** - Even temporarily
2. **Review before push** - Always check `git status`
3. **Use branches** - Keep main stable
4. **Document setup** - Update README with credential instructions
5. **Rotate compromised keys** - If credentials leaked, regenerate immediately

## Quick Reference

```bash
# Status check
git status

# See ignored files
git status --ignored

# Check what will be committed
git diff --cached

# Verify credential protection
git check-ignore shared/config/credentials/*.json

# Safe add (excludes credentials automatically)
git add .

# Commit
git commit -m "Your message"

# Push
git push origin main
```
