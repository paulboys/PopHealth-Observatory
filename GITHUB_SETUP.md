# GitHub Repository Setup Instructions

Follow these steps to create a GitHub repository for your NHANES Data Explorer project.

## 1. Create a new GitHub repository

1. Go to [GitHub](https://github.com/) and sign in to your account.
2. Click the "+" button in the top-right corner and select "New repository".
3. Name your repository: `pophealth-observatory`.
4. Add a description (suggested): `Open-source population health & nutrition analytics toolkit (NHANES focus).`
5. Choose whether to make it public or private.
6. Check "Initialize this repository with a README" (we'll replace it later).
7. Select "MIT License" from the license dropdown.
8. Click "Create repository".

## 2. Initialize Git and push your project

Open a terminal in your NHANES Data Explorer directory and run the following commands:

git commit -m "Initial commit: NHANES Data Explorer"
```powershell
# Initialize (if not already)
git init

# Add all files
git add .

# Commit (skip if already committed)
git commit -m "Initial commit: PopHealth Observatory"

# Add remote (replace YOUR-USERNAME)
git remote add origin https://github.com/YOUR-USERNAME/pophealth-observatory.git

# Ensure branch name is main
git branch -M main

# Push
git push -u origin main
```

Replace `YOUR-USERNAME` with your actual GitHub username.

## 3. Verify your repository

1. Go to your GitHub repository page.
2. Make sure all files are visible and properly formatted.
3. Check that the README.md is displayed correctly on the repository homepage.

## 4. Set up GitHub Pages (optional)

To create a simple website for your project:

1. Go to your repository settings.
2. Scroll down to the "GitHub Pages" section.
3. Under "Source", select the branch you want to publish (e.g., "master").
4. Click "Save".

Your project will be published at `https://YOUR-USERNAME.github.io/pophealth-observatory/`.

## 5. Share your repository

Share the link to your repository with others so they can use your NHANES Data Explorer tool!
