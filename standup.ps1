Set-Location $PSScriptRoot
claude -p "Read data/tasks.json and the git log since yesterday; write a three-line standup to data/standup.md" --allowedTools "Read,Write,Bash(git log:*)"
